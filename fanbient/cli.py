"""fanbient — ambient smart fan system CLI."""

from __future__ import annotations

import logging
import signal
import threading

import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from fanbient.audio.classifier import PantingClassifier
from fanbient.config import FanbientConfig
from fanbient.service import FanbientService

app = typer.Typer(help="fanbient — ambient smart fan system")
console = Console()


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


def _build_config(
    mqtt_host: str, mqtt_port: int, zone: str,
    cooldown: float, temp: bool, thermal: bool,
) -> FanbientConfig:
    config = FanbientConfig()
    config.mqtt.host = mqtt_host
    config.mqtt.port = mqtt_port
    config.mqtt.zone = zone
    config.fan.cooldown_seconds = cooldown
    config.temperature.enabled = temp
    config.thermal_camera.enabled = thermal
    return config


@app.command()
def run(
    log_level: str = typer.Option("INFO", "--log-level", "-l", help="Log level"),
    mqtt_host: str = typer.Option("localhost", "--mqtt-host", help="MQTT broker host"),
    mqtt_port: int = typer.Option(1883, "--mqtt-port", help="MQTT broker port"),
    zone: str = typer.Option("bedroom", "--zone", "-z", help="Zone name"),
    cooldown: float = typer.Option(300.0, "--cooldown", "-c", help="Cooldown seconds after trigger clears"),
    temp: bool = typer.Option(False, "--temp", "-t", help="Enable temperature sensing"),
    thermal: bool = typer.Option(False, "--thermal", help="Enable thermal camera"),
    model: str | None = typer.Option(None, "--model", "-m", help="Path to trained classifier model (.pkl)"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Dry run (no MQTT actuation)"),
) -> None:
    """Run the fanbient ambient fan controller."""
    _setup_logging(log_level)

    config = _build_config(mqtt_host, mqtt_port, zone, cooldown, temp, thermal)
    console.print("[bold green]fanbient[/] starting...", highlight=False)
    _print_config(config, dry_run)

    service = FanbientService(config, dry_run=dry_run)

    # Print events to console
    def on_event(event: str, data: dict) -> None:
        if event == "fan_change":
            s = "[green]ON[/]" if data["on"] else "[red]OFF[/]"
            console.print(f"Fan: {s}")
        elif event == "state_change":
            console.print(f"State: [cyan]{data['state']}[/] (trigger={data.get('trigger')})")

    service.on_event(on_event)

    stop_event = threading.Event()

    def _signal_handler(sig, frame):
        console.print("\n[yellow]Shutting down...[/]")
        stop_event.set()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    if not model:
        console.print("[yellow]No trained model — using heuristic detector[/]")

    # Start service in background, block main thread until signal
    service.start(model_path=model, background=True)
    console.print("[bold green]Running[/] — press Ctrl+C to stop")

    stop_event.wait()
    service.stop()
    console.print("[bold green]fanbient[/] stopped")


@app.command()
def train(
    data_dir: str = typer.Argument(..., help="Directory with panting/ and not_panting/ subdirs of .wav files"),
    output: str = typer.Option("model.pkl", "--output", "-o", help="Output model path"),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
) -> None:
    """Train the panting classifier from labeled audio samples."""
    import numpy as np

    _setup_logging(log_level)

    from pathlib import Path

    import librosa

    config = FanbientConfig()
    data_path = Path(data_dir)

    panting_dir = data_path / "panting"
    not_panting_dir = data_path / "not_panting"

    if not panting_dir.exists() or not not_panting_dir.exists():
        console.print(
            f"[red]Expected subdirectories:[/] {panting_dir} and {not_panting_dir}"
        )
        raise typer.Exit(1)

    chunks: list[np.ndarray] = []
    labels: list[int] = []
    sr = config.audio.sample_rate
    chunk_samples = int(sr * config.audio.chunk_duration)

    for label, subdir in [(1, panting_dir), (0, not_panting_dir)]:
        wav_files = list(subdir.glob("*.wav"))
        console.print(f"Found [cyan]{len(wav_files)}[/] files in {subdir.name}/")
        for wav in wav_files:
            audio, _ = librosa.load(str(wav), sr=sr, mono=True)
            for i in range(0, len(audio) - chunk_samples + 1, chunk_samples):
                chunks.append(audio[i : i + chunk_samples])
                labels.append(label)

    console.print(f"Total chunks: [cyan]{len(chunks)}[/] (panting={sum(labels)}, other={len(labels)-sum(labels)})")

    classifier = PantingClassifier(config.audio)
    metrics = classifier.train(chunks, labels)
    classifier.save(output)

    table = Table(title="Training Results")
    table.add_column("Metric")
    table.add_column("Value")
    for k, v in metrics.items():
        table.add_row(k, f"{v:.3f}" if isinstance(v, float) else str(v))
    console.print(table)


@app.command()
def status(
    mqtt_host: str = typer.Option("localhost", "--mqtt-host"),
    mqtt_port: int = typer.Option(1883, "--mqtt-port"),
    zone: str = typer.Option("bedroom", "--zone", "-z"),
) -> None:
    """Show current system status via MQTT."""
    from fanbient.mqtt.client import FanbientMQTT

    config = FanbientConfig()
    config.mqtt.host = mqtt_host
    config.mqtt.port = mqtt_port
    config.mqtt.zone = zone

    client = FanbientMQTT(config.mqtt)
    results: dict[str, str] = {}
    done = threading.Event()

    def on_msg(topic: str, payload) -> None:
        results[topic] = str(payload)
        if len(results) >= 2:
            done.set()

    try:
        client.connect()
        client.subscribe(f"fanbient/{zone}/#", on_msg)
        client.subscribe("fanbient/system/#", on_msg)
        done.wait(timeout=3.0)

        if results:
            table = Table(title="fanbient Status")
            table.add_column("Topic")
            table.add_column("Value")
            for topic, value in sorted(results.items()):
                table.add_row(topic, value)
            console.print(table)
        else:
            console.print("[yellow]No status messages received (is fanbient running?)[/]")
    except Exception as e:
        console.print(f"[red]Cannot connect to MQTT:[/] {e}")
    finally:
        client.disconnect()


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", help="API host"),
    port: int = typer.Option(8000, "--port", "-p", help="API port"),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
) -> None:
    """Start the FastAPI REST server wrapping the fanbient service."""
    _setup_logging(log_level)
    import uvicorn
    from fanbient.api import create_app
    api_app = create_app()
    console.print(f"[bold green]fanbient API[/] on http://{host}:{port}")
    uvicorn.run(api_app, host=host, port=port, log_level=log_level.lower())


def _print_config(config: FanbientConfig, dry_run: bool) -> None:
    table = Table(title="Configuration")
    table.add_column("Setting")
    table.add_column("Value")
    table.add_row("MQTT", f"{config.mqtt.host}:{config.mqtt.port}")
    table.add_row("Zone", config.mqtt.zone)
    table.add_row("Audio device", str(config.audio.device or "default"))
    table.add_row("Chunk duration", f"{config.audio.chunk_duration}s")
    table.add_row("Cooldown", f"{config.fan.cooldown_seconds}s")
    table.add_row("Temp sensing", "enabled" if config.temperature.enabled else "disabled")
    table.add_row("Thermal camera", "enabled" if config.thermal_camera.enabled else "disabled")
    table.add_row("Dry run", str(dry_run))
    console.print(table)
