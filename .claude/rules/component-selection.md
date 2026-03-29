# Component Selection Rules

## Lifecycle Status

- **Active** — always preferred
- **NRND (Not Recommended for New Designs)** — warn user, suggest active alternative
- **Obsolete/EOL** — never select. If user specifically asks for an obsolete part, warn and provide alternatives
- Always check lifecycle status before recommending any component

## Application-Specific Qualification

### Automotive
- ICs: require AEC-Q100 qualification
- Passives: require AEC-Q200 qualification
- Connectors: require AEC-Q200 or equivalent
- If user mentions "automotive", "vehicle", "car", "ECU" → apply these rules automatically

### Medical
- Require documented PPAP (Production Part Approval Process)
- Prefer components with full lot traceability
- If user mentions "medical", "implant", "patient", "IEC 60601" → apply these rules automatically

### Industrial
- Extended temperature range (-40°C to +85°C minimum)
- If user mentions "industrial", "factory", "PLC" → apply automatically

### Consumer/General
- No special qualification required unless user specifies
- Commercial temperature range (0°C to +70°C) acceptable

## Temperature Grade Mapping

- **Commercial**: 0°C to +70°C
- **Industrial**: -40°C to +85°C
- **Extended**: -40°C to +105°C (sometimes +125°C)
- **Automotive/Military**: -40°C to +125°C (or +150°C)
- If user specifies an exact range (e.g., "-20°C to 80°C"), filter strictly by that range — do not round to a standard grade

## Preferred Packages (default unless user specifies)

- Resistors/Capacitors: 0402, 0603, 0805 (prefer 0603 as default)
- Small ICs: SOT-23, SOT-223, SOT-363
- Medium ICs: SOIC-8/14/16, TSSOP
- Large ICs: QFP, QFN, BGA (only if required by part)
- Through-hole: only if user explicitly requests or component only exists in TH

## Preferred Manufacturers (by category)

These are suggestions, not hard filters. User preference overrides.

- **Resistors/Capacitors**: Yageo, Samsung Electro-Mechanics, Murata, TDK, Vishay
- **Electrolytic capacitors**: Nichicon, Rubycon, Panasonic
- **Op-amps/Analog**: Texas Instruments, Analog Devices, Microchip
- **MCUs**: STMicroelectronics, Microchip, NXP, Espressif
- **Power**: Texas Instruments, Infineon, ON Semiconductor, Rohm
- **Connectors**: Molex, TE Connectivity, Amphenol, Wurth Elektronik
- **LEDs**: Wurth Elektronik, Kingbright, Lumileds

## Derating Rules

- **Ceramic capacitors (MLCC)**: derate voltage rating by 50% for Class II (X5R, X7R). A 10V-rated X7R cap should be used at max 5V.
- **Electrolytic capacitors**: derate voltage by 20%. Derate temperature by 10°C from max rating.
- **Resistors**: max continuous power = 50% of rated power in typical designs
- Mention derating in recommendations if the user's operating conditions are close to component limits
