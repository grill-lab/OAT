from decimal import Decimal


def convert_floats_to_decimals(obj):

    if type(obj) == dict:
        for key, value in obj.items():
            obj[key] = convert_floats_to_decimals(value)
        return obj
    elif type(obj) == list:
        return [convert_floats_to_decimals(el) for el in obj]
    elif type(obj) == float:
        return Decimal(str(obj))
    else:
        return obj


def convert_decimals_to_float(obj):

    if type(obj) == dict:
        for key, value in obj.items():
            obj[key] = convert_decimals_to_float(value)
        return obj
    elif type(obj) == list:
        return [convert_decimals_to_float(el) for el in obj]
    elif type(obj) == Decimal:
        return float(obj)
    else:
        return obj
