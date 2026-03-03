
# fanbient - ambient smart fan++

## seed thoughts

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

battery and ac for flexibility, also articulating armature for precise
positioning, future potential for automatic positioning so it puts itself away
when not needed

also extension for aromatherapy, lighting, ambient sound, etc. via mqtt
triggers and additional lms/mechanisms

everything defaults to full automation with optional guidance or
manual/traditional switching

poc built from composable, cots components (e.g. pc fan, m5stack components,
rpi5, dji/hollyland wireless mic kit, etc.), w/ wildcard being temperature
sensor for leigh when sleeping (e.g. apple watch + ios sensor logger vs bed
topper/strap, etc.)
