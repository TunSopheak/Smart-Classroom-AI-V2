# Phase 19: Safe Hardware Light Prototype Preparation Plan

Smart Classroom AI Monitoring - Production Roadmap Before Flutter

## Current Situation

The real GPIO/LED hardware parts are not available yet.

Because of that, Phase 19 will be prepared in two safe steps:

```text
Phase 19A: Hardware preparation plan
Phase 19B: Software-ready GPIO/LED mode after hardware is available
```

## Important Safety Rule

Do not connect Raspberry Pi directly to classroom AC 220V lights.

Use a safe low-voltage LED prototype first. Real AC light control should only be done later with a proper relay module and electrical safety support.

## Required Parts for LED Prototype

Minimum parts:

```text
1. LED x 2
2. Resistor 220 ohm or 330 ohm x 2
3. Jumper wires female-to-male or female-to-female
4. Breadboard
```

Optional parts:

```text
1. 5V relay module for later relay testing
2. External 5V power supply for relay module
3. Multimeter
4. Small lamp/LED module for safer demo
```

## Planned GPIO Pins

Software light mapping:

```text
Light 1 -> GPIO17 -> Physical Pin 11
Light 2 -> GPIO27 -> Physical Pin 13
GND     -> Physical Pin 6 or 9
```

## Planned Wiring for Light 1 LED

```text
GPIO17 / Physical Pin 11 -> Resistor 220 ohm or 330 ohm -> LED long leg (+)
LED short leg (-) -> GND / Physical Pin 6 or 9
```

## Planned Wiring for Light 2 LED

```text
GPIO27 / Physical Pin 13 -> Resistor 220 ohm or 330 ohm -> LED long leg (+)
LED short leg (-) -> GND / Physical Pin 6 or 9
```

## Current Project Status Before Hardware

The project already supports:

```text
Raspberry Pi client heartbeat
Camera snapshot upload
Auto AI analysis
Occupancy sync
Software light sync
Dashboard near-live monitoring
```

## Next Safe Development Step Without Hardware

Prepare software so the Raspberry Pi client can support two modes:

```text
Software Demo Mode: current safe mode, no GPIO required
GPIO LED Mode: future hardware mode when LED/resistor/breadboard are available
```

This allows the project to continue without blocking on hardware.

## Phase Status

```text
Phase 19: PREPARATION STARTED
Hardware prototype: WAITING FOR PARTS
```
