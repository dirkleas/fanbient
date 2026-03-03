
# fanbient - ambient, smart fan++

## seed thoughts

target audience references: leigh (wife), and tiggy (pug puppy)

autonomous solution for keeping tiggy cool at night (e.g. fan + mic +
edge lm + smart switch + mqtt for tracking sleep states, etc.)

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

poc built from composable, cots components (e.g. pc fan, m5stack components, etc.)
