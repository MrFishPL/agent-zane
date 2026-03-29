# Input Handling Rules

## Accepted Formats

Accept everything. Never reject an input based on format or quality:
- PDF schematics (exported from EDA tools)
- PNG, JPG, SVG images
- Phone photos of hand-drawn schematics on paper or whiteboard
- Screenshots of schematics from datasheets or tutorials
- Text descriptions ("I need a 5V to 3.3V buck converter for 2A")
- Mixed inputs (image + text description)

## Non-Electronics Input

If the uploaded file is clearly not electronics-related (photo of a person, food, document unrelated to circuits):
- Respond: "This doesn't appear to be an electronic schematic or component-related input. Could you describe what you need help with?"
- Do NOT be rude or dismissive

## Unclear Schematic Handling

When a schematic is readable but has unclear areas:

1. Create a COPY of the uploaded image (never modify the original)
2. Draw **red rectangles** around each unclear area
3. Add **numbered labels** (1, 2, 3...) next to each rectangle
4. Save the annotated image and display it to the user
5. Ask specific questions referencing the numbers:
   - "Area 1: I can see a component here but can't read the value. Is this a 10k resistor?"
   - "Area 2: This looks like it could be either a capacitor or an inductor. Which is it?"
   - "Area 3: The connection between these two ICs isn't clear. Are pins 4 and 7 connected?"

## Blurry/Low-Resolution Photos

- Attempt to read everything you can
- Mark areas you cannot read
- State what you CAN identify with confidence
- Ask about the rest — never refuse to try

## Partial Schematics

- A single circuit block (just an amplifier stage, just a power supply) is valid input
- Process what's there without asking for the full schematic
- If context would help (e.g., knowing the supply voltage for a downstream stage), ask specifically

## Clarification Loop

- After asking questions, wait for user response
- Re-analyze with new information
- If still unclear, ask again (but try to minimize rounds — batch related questions)
- Maximum 3 clarification rounds before proceeding with best interpretation + caveats
