"""Module containing class `Calculator`."""


import math
import operator


class CalculatorError(Exception):
    pass


class Calculator:
    
    """
    Postfix calculator.
    
    An instance of this class evaluates postfix expressions, with a
    focus on arithmetic and boolean logic. The syntax and semantics
    of the calculator are similar but not identical to those of a
    small subset of the PostScript programming language.
    """
    
    
    def __init__(self):
        self._dict_stack = _DictionaryStack()
        self._operand_stack = _OperandStack()
    
    
    @property
    def dict_stack(self):
        return self._dict_stack
    
    
    @property
    def operand_stack(self):
        return self._operand_stack
    
    
    def clear(self):
        self._dict_stack.clear()
        self._operand_stack.clear()
    
    
    def execute(self, code):
        
        tokens = code.split()
        
        for token in tokens:
            
            # integer
            try:
                obj = int(token)
            except ValueError:
                pass
            else:
                self._operand_stack.push(obj)
                continue
            
            # float
            try:
                obj = float(token)
            except ValueError:
                pass
            else:
                self._operand_stack.push(obj)
                continue
            
            # name
            try:
                obj = self._dict_stack.get(token)
            except KeyError:
                raise CalculatorError(f'Unrecognized name "{token}".')
            else:
                if isinstance(obj, _Operator):
                    obj.execute(self)
                else:
                    self._operand_stack.push(obj)


class _DictionaryStack:
    
    
    def __init__(self):
        self._system_dict = _SYSTEM_DICT
        self.clear()
    
    
    def clear(self):
        self._user_dict = {}
    
    
    def get(self, name):
        
        try:
            return self._user_dict[name]
        
        except KeyError:
            
            try:
                return self._system_dict[name]
            
            except KeyError:
                raise CalculatorError(f'Unrecognized name "{name}".')
    
    
    def put(self, name, value):
        self._user_dict[name] = value


class _OperandStack:
    
    
    def __init__(self):
        self.clear()
    
    
    def clear(self):
        self._operands = []
    
    
    def __len__(self):
        return len(self._operands)
    
    
    def push(self, obj):
        self._operands.append(obj)
    
    
    def pop(self):
        try:
            return self._operands.pop()
        except IndexError:
            raise CalculatorError('Attempt to pop from empty operand stack.')
    
    
    def peek(self, operand_count=1):
        
        if len(self) < operand_count:
            
            operand_count = _get_operand_count_text(operand_count)
            
            raise CalculatorError(
                f'Attempt to peek at {operand_count} of operand stack '
                f'that has only {len(self)}.')
        
        else:
            return self._operands[-operand_count:]


def _get_operand_count_text(operand_count):
    suffix = '' if operand_count == 1 else 's'
    return f'{operand_count} operand{suffix}'


class _Type:
    
    def __init__(self, name):
        self._name = name
    
    @property
    def name(self):
        return self._name
    
    def is_instance(self, x):
        raise NotImplementedError()


class _SimpleType(_Type):
    
    def __init__(self, name, included_class_info, excluded_class_info=()):
        super().__init__(name)
        self._included_class_info = included_class_info
        self._excluded_class_info = excluded_class_info
    
    def is_instance(self, x):
        return isinstance(x, self._included_class_info) and \
            not isinstance(x, self._excluded_class_info)


class _AnyType(_Type):
    
    def __init__(self):
        super().__init__('any')
    
    def is_instance(self, _):
        return True


class _UnionType(_Type):
    
    def __init__(self, types):
        name = ' | '.join(t.name for t in types)
        super().__init__(name)
        self._types = tuple(types)
    
    def is_instance(self, x):
        return any(t.is_instance(x) for t in self._types)


# Interpreter value types.
_Boolean = _SimpleType('boolean', bool)
_Integer = _SimpleType('integer', int, bool)
_Float = _SimpleType('float', float)
_String = _SimpleType('string', str)
_Number = _UnionType((_Integer, _Float))
_Any = _AnyType()


def _is_instance(x, arg):
    if isinstance(arg, _Type):
        return arg.is_instance(x)
    else:
        return any(_is_instance(x, t) for t in arg)


class _Operator:
    
    
    def __init__(self, name, operand_types):
        self._name = name
        self._operand_types = operand_types
    
    
    @property
    def name(self):
        return self._name
    
    
    @property
    def operand_types(self):
        return self._operand_types
    
    
    @property
    def operand_count(self):
        return len(self.operand_types)
    
    
    def execute(self, calc):
        raise NotImplementedError()
    
    
    def _check_operand_count(self, calc):
        
        operand_stack = calc.operand_stack
        
        if self.operand_count > len(operand_stack):
            # not enough operands for this operator
            
            required_count = _get_operand_count_text(self.operand_count)
            stack_count = _get_operand_count_text(len(operand_stack))
            
            raise CalculatorError(
                f'Operator "{self.name}" requires {required_count} '
                f'but operand stack contains only {stack_count}.')
    
    
    def _get_operands(self, calc):
        
        self._check_operand_count(calc)
        
        operands = calc.operand_stack.peek(self.operand_count)
        pairs = zip(operands, self.operand_types)
        
        for i, (operand, required_type) in enumerate(pairs):
            
            if not _is_instance(operand, required_type):
 
                value_text = _get_value_text(operand)
                type_name = _get_type_name(required_type)
                
                raise CalculatorError(
                    f'Operator "{self.name}" operand {i + 1} with value '
                    f'{value_text} is not of required type {type_name}.')
        
        return operands


def _get_value_text(x):
    if x is True:
        return 'true'
    elif x is False:
        return 'false'
    elif isinstance(x, str):
        return f'"{x}"'
    else:
        return str(x)


def _get_type_name(arg):
    if isinstance(arg, _Type):
        return arg.name
    else:
        return ' | '.join(_get_type_name(t) for t in arg)


class _ConstantOperator(_Operator):
    
    def __init__(self, name, constant):
        super().__init__(name, ())
        self._constant = constant
        
    def execute(self, calc):
        calc.operand_stack.push(self._constant)


class _Dup(_Operator):
    
    def __init__(self):
        super().__init__('dup', (_Any,))
    
    def execute(self, calc):
        operand, = self._get_operands(calc)
        calc.operand_stack.push(operand)


class _Exch(_Operator):
    
    def __init__(self):
        super().__init__('exch', (_Any, _Any))
    
    def execute(self, calc):
        self._check_operand_count(calc)
        stack = calc.operand_stack
        x = stack.pop()
        y = stack.pop()
        stack.push(x)
        stack.push(y)


class _Pop(_Operator):
    
    def __init__(self):
        super().__init__('pop', (_Any,))
    
    def execute(self, calc):
        self._check_operand_count(calc)
        calc.operand_stack.pop()


class _Clear(_Operator):
    
    def __init__(self):
        super().__init__('clear', ())
    
    def execute(self, calc):
        calc.operand_stack.clear()


class _BinaryOperator(_Operator):
    
    
    def __init__(self, name, operand_types, function):
        super().__init__(name, operand_types)
        self._function = function
        
        
    def execute(self, calc):
        
        # Get operands. Do not modify stack: the stack should be
        # modified only if the operation succeeds.
        x, y = self._get_operands(calc)
        
        try:
            
            # Operate.
            result = self._function(x, y)
            
        except Exception as e:
            # operation failed
            
            raise CalculatorError(
                f'Execution of "{self.name}" operator failed with message: '
                f'{str(e)}')
        
        else:
            # operation succeeded
        
            # Modify stack.
            stack = calc.operand_stack
            stack.pop()
            stack.pop()
            stack.push(result)


class _BinaryArithmeticOperator(_BinaryOperator):
    
    def __init__(self, name, function):
        operand_types = (_Number, _Number)
        super().__init__(name, operand_types, function)


def _div(x, y):
    if y == 0:
        raise CalculatorError('divide by zero.')
    else:
        return x / y


def _mod(x, y):
    if y == 0:
        raise CalculatorError('divide by zero.')
    else:
        return x % y


class _UnaryOperator(_Operator):
    
    
    def __init__(self, name, operator_types, function):
        super().__init__(name, operator_types)
        self._function = function
        
        
    def execute(self, calc):
        
        # Get operand. Do not modify stack: the stack should be
        # modified only if the operation succeeds.
        x, = self._get_operands(calc)
        
        try:
            
            # Operate.
            result = self._function(x)
            
        except Exception as e:
            # operation failed
            
            raise CalculatorError(
                f'Execution of "{self.name}" operator failed with message: '
                f'{str(e)}')
        
        else:
            # operation succeeded
        
            # Modify stack.
            stack = calc.operand_stack
            stack.pop()
            stack.push(result)



class _UnaryArithmeticOperator(_UnaryOperator):
    
    def __init__(self, name, function):
        operand_types = (_Number,)
        super().__init__(name, operand_types, function)
    
    
class _CoercionOperator(_UnaryOperator):
    
    def __init__(self, name, function):
        operand_types = ((_Integer, _Float, _String),)
        super().__init__(name, operand_types, function)


def _boolean(x):
    if x == 'true':
        return True
    elif x == 'false':
        return False
    else:
        x = _get_value_text(x)
        raise CalculatorError(f'cannot coerce {x}.')


def _integer(x):
    return _coerce(x, int)


def _coerce(x, type_):
    try:
        return type_(x)
    except Exception:
        x = _get_value_text(x)
        raise CalculatorError(f'cannot coerce {x}.')


def _float(x):
    return _coerce(x, float)


class _ComparisonOperator(_BinaryOperator):
    
    
    def __init__(self, name, function):
        operand_types = (_Any, _Any)
        super().__init__(name, operand_types, function)


def _eq(x, y):
    
    # In most circumstances we delegate to Python's == operator.
    # That operator compares False and True as though they were 0
    # and 1, respectively, however, which we do not want. We deal
    # with this by returning False if one operand is boolean and
    # the other is not.
    
    is_boolean = _Boolean.is_instance
    
    if is_boolean(x) == is_boolean(y):
        # either both operands are boolean or both are non-boolean
        
        return x == y
           
    else:
        # one operand is boolean and the other is not
        
        return False


def _ne(x, y):
    return not _eq(x, y)


def _gt(x, y):
    return _compare(x, y, operator.gt)


def _compare(x, y, op):
    
    # In most circumstances we delegate to Python's comparison operators.
    # Those operators compare False and True as though they were 0 and 1,
    # respectively, however, which we do not want. We deal with this by
    # raising an exception if one operand is boolean and the other is not.
    
    is_boolean = _Boolean.is_instance
    
    if is_boolean(x) == is_boolean(y):
        # either both operands are boolean or both are non-boolean
        
        try:
            return op(x, y)
        except Exception:
            pass
    
    # If we get here, either one operand is boolean and the other is
    # not or `op` raised an exception.
    
    x = _get_value_text(x)
    y = _get_value_text(y)
    raise CalculatorError(f'cannot compare {x} and {y}.')


def _ge(x, y):
    return _compare(x, y, operator.ge)


def _lt(x, y):
    return _compare(x, y, operator.lt)


def _le(x, y):
    return _compare(x, y, operator.le)


class _BinaryLogicalOperator(_BinaryOperator):
    
    def __init__(self, name, function):
        operand_types = (_Boolean, _Boolean)
        super().__init__(name, operand_types, function)


class _UnaryLogicalOperator(_UnaryOperator):
    
    def __init__(self, name, function):
        operand_types = (_Boolean,)
        super().__init__(name, operand_types, function)


_OPERATORS = (
    
    # constants
    _ConstantOperator('true', True),
    _ConstantOperator('false', False),
    
    # stack manipulation
    _Dup(),
    _Exch(),
    _Pop(),
    _Clear(),
    
    # binary arithmetic
    _BinaryArithmeticOperator('add', operator.add),
    _BinaryArithmeticOperator('sub', operator.sub),
    _BinaryArithmeticOperator('mul', operator.mul),
    _BinaryArithmeticOperator('div', _div),
    _BinaryArithmeticOperator('mod', _mod),
    _BinaryArithmeticOperator('pow', operator.pow),
     
    # unary arithmetic
    _UnaryArithmeticOperator('neg', operator.neg),
    _UnaryArithmeticOperator('abs', abs),
    _UnaryArithmeticOperator('ceiling', math.ceil),
    _UnaryArithmeticOperator('floor', math.floor),
    _UnaryArithmeticOperator('round', round),
    _UnaryArithmeticOperator('exp', math.exp),
    _UnaryArithmeticOperator('ln', math.log),
    _UnaryArithmeticOperator('log2', math.log2),
    _UnaryArithmeticOperator('log10', math.log10),
     
    # coercion
    _CoercionOperator('boolean', _boolean),
    _CoercionOperator('integer', _integer),
    _CoercionOperator('float', _float),
     
    # comparison
    _ComparisonOperator('eq', _eq),
    _ComparisonOperator('ne', _ne),
    _ComparisonOperator('gt', operator.gt),
    _ComparisonOperator('ge', operator.ge),
    _ComparisonOperator('lt', operator.lt),
    _ComparisonOperator('le', operator.le),
     
    # logic
    _BinaryLogicalOperator('and', operator.and_),
    _BinaryLogicalOperator('or', operator.or_),
    _BinaryLogicalOperator('xor', operator.xor),
    _UnaryLogicalOperator('not', operator.not_),

)


_SYSTEM_DICT = dict((op.name, op) for op in _OPERATORS)
