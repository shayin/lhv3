from src.backend.api.strategy_routes import load_strategy_from_code

path = 'src/backend/strategy/extremum_strategy_v5.py'
code = open(path, 'r', encoding='utf-8').read()

try:
    inst = load_strategy_from_code(code, data=None, parameters=None)
    print('实例化成功:', type(inst), inst.name)
except Exception as e:
    import traceback
    traceback.print_exc()
    print('加载失败:', e)
