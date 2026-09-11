from pivl import Action, PIVLEngine, RuleCompiler, SQLiteRegistry, Verifier

registry = SQLiteRegistry(":memory:")
compiler = RuleCompiler()
registry.add_rule(compiler.compile("before submit, oracle_score must equal 1", priority=100))
registry.add_rule(compiler.compile("before submit, nop_score must equal 0", priority=100))
engine = PIVLEngine(registry, Verifier())
state = {}

def execute(action, state):
    if action.name == "run_oracle": state["oracle_score"] = 1
    elif action.name == "run_nop": state["nop_score"] = 0
    elif action.name == "submit": state["submitted"] = True
    return state

for name in ["submit", "run_nop", "submit", "run_oracle", "submit"]:
    result = engine.step(Action(name), state, execute)
    print(name, "EXECUTED" if result.executed else "BLOCKED")
    for failure in result.pre_report.failures:
        print(" -", failure.reason)

print("state:", state)
print("failures remembered:", len(registry.list_failures()))
print("prevention rules:", len([r for r in registry.list_rules() if r.source == "failure-derived"]))
