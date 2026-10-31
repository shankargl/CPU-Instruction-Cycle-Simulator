
const $ = (id) => document.getElementById(id);

const defaultProgram = `LDI 10
STORE 0
LDI 5
ADD 0
STORE 1
HALT`;

let cpuState = null;
let toastTimer = null;

// Show notification
function notify(message) {
    const toast = $("toast");

    toast.textContent = message;
    toast.classList.add("show");

    clearTimeout(toastTimer);

    toastTimer = setTimeout(() => {
        toast.classList.remove("show");
    }, 3200);
}

// Communicate with Flask backend
async function api(url, body) {

    const response = await fetch(url, {
        method: body ? "POST" : "GET",

        headers: body
            ? { "Content-Type": "application/json" }
            : {},

        body: body
            ? JSON.stringify(body)
            : undefined
    });

    const data = await response.json();

    if (!response.ok) {
        const error = new Error(
            data.error || "Something went wrong."
        );

        error.state = data.state;
        throw error;
    }

    return data;
}

// Determine current CPU phase
function phaseName(state) {

    if (state.halted) {
        return "HALTED";
    }

    return ["FETCH", "DECODE", "EXECUTE"][state.phase];
}

// Render complete CPU dashboard
function render(state) {

    cpuState = state;

    const r = state.registers;

    // Update CPU registers
    $("cycles").textContent = state.cycles;

    $("regPC").textContent = r.PC;
    $("regIR").textContent = r.IR;
    $("regMAR").textContent = r.MAR;
    $("regMDR").textContent = r.MDR;
    $("regACC").textContent = r.ACC;
    $("regZF").textContent = r.ZF;

    // Update current instruction
    $("currentInstruction").textContent =
        state.current
            ? state.current.source
            : "—";

    // Update status
    $("statusLabel").textContent = phaseName(state);

    $("statusMessage").textContent = state.message;

    $("cpuStatus").textContent =
        state.halted ? "HALTED" : "RUNNING";

    // Disable buttons after HALT
    $("stepBtn").disabled = state.halted;
    $("runBtn").disabled = state.halted;

    // Update Fetch Decode Execute indicators
    const phaseIndex = state.halted ? 3 : state.phase;

    const phases = [
        "phaseFetch",
        "phaseDecode",
        "phaseExecute"
    ];

    phases.forEach((id, i) => {

        const element = $(id);

        element.classList.toggle(
            "active",
            i === phaseIndex
        );

        element.classList.toggle(
            "done",
            i < phaseIndex
        );

    });

    // Render data memory
    $("memoryGrid").innerHTML = state.data
        .map((value, i) => {

            const active =
                state.registers.MAR === i
                    ? "active"
                    : "";

            return `
                <div class="memory-cell ${active}">
                    <span>ADDR ${i}</span>
                    <strong>${escapeHtml(value)}</strong>
                </div>
            `;

        }).join("");

    // Render program memory
    $("programRows").innerHTML = state.program
        .map((ins, i) => {

            const currentAddress = state.current
                ? state.registers.MAR
                : state.registers.PC;

            const isCurrent = !state.halted &&
                (
                    state.phase === 0
                        ? i === state.registers.PC
                        : i === currentAddress
                );

            const arg = ins.arg === null
                ? ""
                : ` ${ins.arg}`;

            return `
                <tr class="${isCurrent ? "current-row" : ""}">

                    <td>${i}</td>

                    <td>
                        ${ins.opcode}${arg}
                    </td>

                    <td>
                        ${meaning(ins.opcode, ins.arg)}
                    </td>

                    <td>
                        <span class="row-state">
                            ${isCurrent
                    ? "CURRENT"
                    : i < state.registers.PC
                        ? "PASSED"
                        : "WAITING"
                }
                        </span>
                    </td>

                </tr>
            `;

        }).join("");

}

// Explain instruction meaning
function meaning(op, arg) {

    const map = {

        LDI: `ACC ← ${arg}`,

        LOAD: `ACC ← M[${arg}]`,

        STORE: `M[${arg}] ← ACC`,

        ADD: `ACC ← ACC + M[${arg}]`,

        SUB: `ACC ← ACC − M[${arg}]`,

        MUL: `ACC ← ACC × M[${arg}]`,

        DIV: `ACC ← ACC ÷ M[${arg}]`,

        JMP: `PC ← ${arg}`,

        JZ: `Jump if ZF = 1 to ${arg}`,

        JNZ: `Jump if ZF = 0 to ${arg}`,

        HALT: "Stop execution"

    };

    return map[op] || "";
}

// Prevent HTML injection in displayed values
function escapeHtml(value) {

    return String(value).replace(/[&<>"']/g, c => ({

        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"

    }[c]));

}

// Load program into Flask
async function loadProgram() {

    const program = $("program").value;

    const data = $("memoryInput").value;

    const state = await api("/api/reset", {

        program: program,

        data: data

    });

    render(state);

    notify("Program loaded successfully.");
}

// Get current CPU state
async function refresh() {

    const state = await api("/api/state");

    render(state);

}

// Load example program into editor
$("exampleBtn").addEventListener("click", () => {

    $("program").value = defaultProgram;

    $("memoryInput").value =
        "0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0";

    notify(
        "Example loaded. Click Load / Reset."
    );

});

// Load / Reset button
$("loadBtn").addEventListener("click", async () => {

    try {

        await loadProgram();

    } catch (error) {

        notify(error.message);

    }

});

// Reset button
$("resetBtn").addEventListener("click", async () => {

    try {

        await loadProgram();

    } catch (error) {

        notify(error.message);

    }

});

// Execute one CPU phase
$("stepBtn").addEventListener("click", async () => {

    try {

        const state = await api("/api/phase", {});

        render(state);

    } catch (error) {

        notify(error.message);

        if (error.state) {
            render(error.state);
        }

    }

});

// Execute complete program
$("runBtn").addEventListener("click", async () => {

    try {

        const state = await api("/api/run", {});

        render(state);

        if (state.halted) {
            notify("Program execution completed!");
        }

    } catch (error) {

        notify(error.message);

        if (error.state) {
            render(error.state);
        }

    }

});

// Initialize simulator when page loads
refresh().catch(() => {

    loadProgram().catch(error => {

        notify(error.message);

    });

});
