# CPU Instruction Cycle Simulator (COA)

A medium-level Computer Organization and Architecture mini-project built with Flask, HTML, CSS and JavaScript.

## Features
- Interactive Fetch, Decode and Execute phases.
- Step through one micro-phase at a time or run until HALT.
- Live CPU registers: PC, IR, MAR, MDR, ACC and Zero Flag (ZF).
- 16-location data memory and editable program memory.
- Instruction trace with current instruction highlighting.
- Input validation for invalid instructions, addresses and division by zero.

## Architecture
- `app.py`: Flask routes, instruction parser, CPU state and execution engine.
- `templates/index.html`: simulator interface.
- `static/style.css`: responsive dashboard styling.
- `static/app.js`: API calls and live UI rendering.

The browser sends program and memory values to Flask. Flask parses the assembly-like program and stores the simulator state in the user's Flask session. Each **Next Phase** request advances the CPU by one stage:
1. **Fetch:** PC selects the instruction; MAR/MDR/IR are updated; PC increments.
2. **Decode:** the opcode and operand are interpreted.
3. **Execute:** the operation updates ACC, data memory, PC, flags or halt state.

This is an educational simplified CPU model, not a complete hardware implementation. Program memory and data memory are separate. Arithmetic uses Python integers; DIV performs integer division.

## Supported instruction set

| Instruction | Meaning |
|---|---|
| `LDI n` | ACC = n |
| `LOAD a` | ACC = data memory[a] |
| `STORE a` | data memory[a] = ACC |
| `ADD a` | ACC = ACC + data memory[a] |
| `SUB a` | ACC = ACC - data memory[a] |
| `MUL a` | ACC = ACC * data memory[a] |
| `DIV a` | ACC = ACC // data memory[a] |
| `JMP a` | Unconditional jump to program address a |
| `JZ a` | Jump if zero flag is 1 |
| `JNZ a` | Jump if zero flag is 0 |
| `HALT` | Stop execution |

Addresses are zero-based. Data memory addresses are 0–15. Program addresses range from 0 to the last instruction. Use one instruction per line. Lines beginning with `#`, and inline text after `#`, are comments.

## Run locally

### Windows
```bash
py -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

### macOS / Linux
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m pip install -r requirements.txt
python app.py
```

Open the local URL printed by Flask (normally `http://127.0.0.1:5000`).

## Suggested demo
The default program stores 10 in data memory[0], loads 5 into ACC, adds memory[0], and stores the result (15) in memory[1]. Step through each phase and watch the registers and memory change.
