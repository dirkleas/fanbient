# fanbient - seed thoughts

target audience references: leigh (wife), and tiggy (pug puppy)

primary use case/scenario: getting too hot while sleeping where appropriately
sized fan is viable solution, but don't want fan on all the time as it can get
too cool

autonomous solution for keeping tiggy cool at night (e.g. fan + mic +
edge lm + smart switch + mqtt for tracking sleep states, etc.) triggered on
panting for fan actuation w/ configurable toggle once triggered following no
panting

refactor, switching tiggy panting audio tracking to temp sensor so larger
fan can work for leigh based on her body temperature

tiggy: sound trigger, leigh: temp trigger -- also, low hanging fruit things
like temporal scheduling, etc.

battery and ac for flexibility — [Milwaukee M18](https://www.milwaukeetool.com/products/48-11-1850)
batteries (many on hand, various sizes) via dock adapter + 18V→12V step-down
for fan power, or USB-C PD power banks for RPi5. Also
[Triad Orbit](https://www.triad-orbit.com/) modular armatures (stands, booms,
adapters) for precise positioning of fans, mics, and sensors — future
potential for automatic positioning so it puts itself away when not needed

also extension for aromatherapy, lighting, ambient sound, etc. via mqtt
triggers and additional lms/mechanisms

everything defaults to full automation with optional guidance or
manual/traditional switching

poc built from composable, cots components (e.g. [Noctua](https://noctua.at/) pc fan /
centrifugal blower / inline duct fan (see [fan rationale](docs/hardware.md#fan-design-rationale)),
[M5Stack](https://shop.m5stack.com/) components, [RPi5](https://www.raspberrypi.com/products/raspberry-pi-5/),
[DJI Mic 2](https://store.dji.com/product/dji-mic-2)/[Hollyland Lark M2](https://www.hollyland.com/product/lark-m2) wireless mic kit, etc.),
w/ wildcard being temperature sensor for leigh when sleeping (e.g.
[Apple Watch](https://www.apple.com/apple-watch/) + [Sensor Logger](https://apps.apple.com/app/sensor-logger/id1531582925)
vs bed topper/strap, etc.)
