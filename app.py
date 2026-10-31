from flask import Flask, render_template, request, jsonify, session
from copy import deepcopy
import re
import os

app = Flask(__name__)
app.secret_key = os.environ.get(
    "SECRET_KEY",
    "development-secret-key"
)

DEFAULT_PROGRAM = """LDI 10
STORE 0
LDI 5
ADD 0
STORE 1
HALT"""
DEFAULT_DATA = [0] * 16

INSTRUCTIONS = {
    "LDI": "Load an immediate value into ACC",
    "LOAD": "Load data memory[address] into ACC",
    "STORE": "Store ACC into data memory[address]",
    "ADD": "Add data memory[address] to ACC",
    "SUB": "Subtract data memory[address] from ACC",
    "MUL": "Multiply ACC by data memory[address]",
    "DIV": "Divide ACC by data memory[address] (integer division)",
    "JMP": "Jump to a program instruction address",
    "JZ": "Jump if the zero flag is set",
    "JNZ": "Jump if the zero flag is not set",
    "HALT": "Stop program execution",
}

def parse_program(source):
    program = []
    for line_no, raw in enumerate(source.splitlines(), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = re.split(r"\s+", line)
        opcode = parts[0].upper()
        if opcode not in INSTRUCTIONS:
            raise ValueError(f"Line {line_no}: unknown instruction '{opcode}'.")
        needs_arg = opcode != "HALT"
        if needs_arg and len(parts) != 2:
            raise ValueError(f"Line {line_no}: {opcode} requires exactly one argument.")
        if not needs_arg and len(parts) != 1:
            raise ValueError(f"Line {line_no}: HALT takes no argument.")
        arg = None
        if needs_arg:
            try:
                arg = int(parts[1], 0)
            except ValueError:
                raise ValueError(f"Line {line_no}: argument must be an integer.")
        program.append({"opcode": opcode, "arg": arg, "source": line})
    if not program:
        raise ValueError("Program is empty.")
    return program

def fresh_state(program_source=DEFAULT_PROGRAM, data_values=None):
    program = parse_program(program_source)
    data = list(data_values if data_values is not None else DEFAULT_DATA)
    if len(data) != 16:
        raise ValueError("Data memory must contain exactly 16 integer values.")
    return {
        "program": program,
        "data": data,
        "registers": {"PC": 0, "IR": "—", "MAR": "—", "MDR": "—", "ACC": 0, "ZF": 1},
        "phase": 0,
        "current": None,
        "halted": False,
        "message": "Program loaded. Press Next Phase to begin.",
        "last_action": "Ready",
        "cycles": 0,
    }

def get_state():
    if "cpu" not in session:
        session["cpu"] = fresh_state()
    return session["cpu"]

def save_state(state):
    session["cpu"] = state
    session.modified = True

def check_address(address, size, label):
    if address is None or not 0 <= address < size:
        raise ValueError(f"{label} address {address} is outside valid range 0–{size - 1}.")

def update_flags(state):
    state["registers"]["ZF"] = 1 if state["registers"]["ACC"] == 0 else 0

def advance_phase(state):
    if state["halted"]:
        return state
    regs = state["registers"]
    phase = state["phase"]

    if phase == 0:  # FETCH
        pc = regs["PC"]
        check_address(pc, len(state["program"]), "Program")
        instruction = state["program"][pc]
        state["current"] = deepcopy(instruction)
        regs["MAR"] = pc
        regs["MDR"] = instruction["source"]
        regs["IR"] = instruction["source"]
        regs["PC"] = pc + 1
        state["phase"] = 1
        state["last_action"] = f"FETCH: instruction at program address {pc} moved into IR."
        state["message"] = "Instruction fetched. The PC now points to the next instruction."
    elif phase == 1:  # DECODE
        if not state["current"]:
            raise ValueError("No instruction is available to decode.")
        ins = state["current"]
        state["phase"] = 2
        arg_text = "" if ins["arg"] is None else f" {ins['arg']}"
        state["last_action"] = f"DECODE: identified {ins['opcode']}{arg_text}."
        state["message"] = INSTRUCTIONS[ins["opcode"]]
    else:  # EXECUTE
        ins = state["current"]
        if not ins:
            raise ValueError("No instruction is available to execute.")
        op, arg = ins["opcode"], ins["arg"]
        if op == "LDI":
            regs["ACC"] = arg
            update_flags(state)
        elif op in ("LOAD", "ADD", "SUB", "MUL", "DIV", "STORE"):
            check_address(arg, len(state["data"]), "Data memory")
            regs["MAR"] = arg
            if op == "LOAD":
                regs["MDR"] = state["data"][arg]
                regs["ACC"] = state["data"][arg]
                update_flags(state)
            elif op == "STORE":
                state["data"][arg] = regs["ACC"]
                regs["MDR"] = regs["ACC"]
            else:
                regs["MDR"] = state["data"][arg]
                value = state["data"][arg]
                if op == "ADD":
                    regs["ACC"] += value
                elif op == "SUB":
                    regs["ACC"] -= value
                elif op == "MUL":
                    regs["ACC"] *= value
                elif op == "DIV":
                    if value == 0:
                        raise ValueError("Division by zero: data memory value is 0.")
                    regs["ACC"] //= value
                update_flags(state)
        elif op == "JMP":
            check_address(arg, len(state["program"]), "Program")
            regs["PC"] = arg
        elif op == "JZ":
            if regs["ZF"] == 1:
                check_address(arg, len(state["program"]), "Program")
                regs["PC"] = arg
        elif op == "JNZ":
            if regs["ZF"] == 0:
                check_address(arg, len(state["program"]), "Program")
                regs["PC"] = arg
        elif op == "HALT":
            state["halted"] = True
        state["phase"] = 0
        state["current"] = None
        state["cycles"] += 1
        state["last_action"] = f"EXECUTE: {op}" + (f" {arg}" if arg is not None else "") + " completed."
        state["message"] = "CPU halted." if state["halted"] else "Instruction completed. Ready to fetch the next instruction."
    return state

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/state")
def api_state():
    return jsonify(get_state())

@app.route("/api/reset", methods=["POST"])
def api_reset():
    payload = request.get_json(silent=True) or {}
    try:
        source = payload.get("program", DEFAULT_PROGRAM)
        raw_data = payload.get("data", ",".join(map(str, DEFAULT_DATA)))
        if isinstance(raw_data, str):
            data = [int(x.strip(), 0) for x in raw_data.split(",") if x.strip()]
        else:
            data = [int(x) for x in raw_data]
        state = fresh_state(source, data)
        save_state(state)
        return jsonify(state)
    except (ValueError, TypeError) as exc:
        return jsonify({"error": str(exc)}), 400

@app.route("/api/phase", methods=["POST"])
def api_phase():
    state = deepcopy(get_state())
    try:
        advance_phase(state)
        save_state(state)
        return jsonify(state)
    except (ValueError, TypeError) as exc:
        state["message"] = str(exc)
        save_state(state)
        return jsonify({"error": str(exc), "state": state}), 400

@app.route("/api/run", methods=["POST"])
def api_run():
    state = deepcopy(get_state())
    try:
        # Run until HALT or a safety limit; each instruction has three phases.
        for _ in range(300):
            if state["halted"]:
                break
            advance_phase(state)
        else:
            raise ValueError("Execution stopped after 300 phases to prevent an infinite loop.")
        save_state(state)
        return jsonify(state)
    except (ValueError, TypeError) as exc:
        state["message"] = str(exc)
        save_state(state)
        return jsonify({"error": str(exc), "state": state}), 400

if __name__ == "__main__":
    app.run(debug=True)
