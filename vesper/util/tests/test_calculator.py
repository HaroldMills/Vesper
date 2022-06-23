import math

from vesper.tests.test_case import TestCase
from vesper.util.calculator import Calculator, CalculatorError


class CalculatorTests(TestCase):


    def setUp(self):
        self.calculator = Calculator()
    
    
    def test_nonnumeric_operators(self):
        
        cases = {
            
            
            # constants
            
            'true': (
                ([], True),
            ),
            
            'false': (
                ([], False),
            ),
            
            
            # stack manipulation
            
            'dup': (
                ([1], [1, 1]),
                ([True], [True, True]),
                ([1, 2], [1, 2, 2]),
            ),
            
            'exch': (
                ([1, True], [True, 1]),
                ([False, 1, True], [False, True, 1]),
            ),
            
            'pop': (
                ([1], []),
                ([1, 2], [1]),
            ),
            
            'clear': (
                ([1], []),
                ([1, 2], []),
            ),
            
            
        }
        
        for operator_name, stack_pairs in cases.items():
            # print(f'testing "{operator_name}" operator...')
            for initial_stack, final_stack in stack_pairs:
                self._set_up(initial_stack)
                self.calculator.execute(operator_name)
                self._assert_calculator(final_stack)
    
    
    def test_numeric_operators(self):
        
        # We test operators that yield a single number separately
        # from other operators so we can check the result type.
        
        cases = {
            
            
            # binary arithmetic
            
            'add': (
                ([1, 2], 3),
                ([1, 2.5], 3.5),
                ([-2, 1.], -1.),
            ),
            
            'sub': (
                ([1, 2], -1),
                ([1., -2], 3.),
            ),
            
            'mul': (
                ([2, 3], 6),
                ([2., 3.5], 7.),
            ),
            
            'div': (
                ([4, 2], 2.),
                ([2., 4], .5),
                ([2, .5], 4.),
            ),
            
            'mod': (
                ([3, 2], 1),
                ([3, 2.5], .5),
                ([4.5, 3], 1.5),
            ),
            
            'pow': (
                ([2, 3], 8),
                ([4, .5], 2.),
                ([-2, 3], -8),
                ([2, -2], .25),
            ),
            
            
            # unary arithmetic
            
            'neg': (
                (0, 0),
                (1, -1),
                (-1.5, 1.5),
            ),
            
            'abs': (
                (0, 0),
                (1, 1),
                (-1.5, 1.5),
            ),
            
            'ceiling': (
                (0, 0),
                (1, 1),
                (1.5, 2),
                (-1.5, -1),
            ),
            
            'floor': (
                (0, 0),
                (1, 1),
                (1.5, 1),
                (-1.5, -2),
            ),
            
            'round': (
                (0, 0),
                (1, 1),
                (1.1, 1),
                (1.5, 2),
                (1.9, 2),
                (2.5, 2),
                (-1.1, -1),
                (-1.5, -2),
            ),
            
            'exp': (
                (0, 1.),
                (1, math.e),
                (1.1, math.e ** 1.1),
                (-1.1, math.e ** -1.1),
            ),
            
            'ln': (
                (1, 0.),
                (math.e, 1.),
                (1.1, math.log(1.1)),
            ),
            
            'log2': (
                (1, 0.),
                (2, 1.),
                (1.1, math.log2(1.1)),
            ),
            
            'log10': (
                (1, 0.),
                (10, 1.),
                (1.1, math.log10(1.1)),
            ),
            
            
            # coercion
            
            'boolean': (
                ('true', True),
                ('false', False),
            ),
            
            'integer': (
                (0, 0),
                (1, 1),
                (1.1, 1),
                (1.9, 1),
                (-1.1, -1),
                (-1.9, -1),
                ('123', 123),
                ('-123', -123),
            ),
            
            'float': (
                (0, 0.),
                (1, 1.),
                (1.1, 1.1),
                (-1, -1.),
                ('1', 1.),
                ('1.', 1.),
                ('1.2', 1.2),
                ('-1.2', -1.2),
            ),
        
        
        }
        
        c = self.calculator
        
        for operator_name, pairs in cases.items():
            # print(f'testing "{operator_name}" operator...')
            for initial_stack, expected in pairs:
                self._set_up(initial_stack)
                c.execute(operator_name)
                actual = c.operand_stack.pop()
                self.assertEqual(actual, expected)
                self.assertEqual(type(actual), type(expected))
    
    
    def test_comparison_operators(self):
        
        
        cases = {
            
            
            ('eq', 'ne'): (
            
                # booleans
                ([False, False], True),
                ([False, True], False),
                ([True, False], False),
                ([True, True], True),
                
                # boolean and number
                ([False, 1], False),
                ([False, 1.], False),
                ([False, -1], False),
                ([True, 0], False),
                ([True, 0.], False),
                ([True, -1], False),
                
                # Make sure we don't delegate to Python in these cases,
                # for which Python yields `True`.
                ([False, 0], False),
                ([False, 0.], False),
                ([True, 1], False),
                ([True, 1.], False),
                
                # boolean and string
                ([False, ''], False),
                ([True, 'True'], False),
                
                # numbers
                ([0, 0], True),
                ([0, 1], False),
                ([1., 1.], True),
                ([1., 0.], False),
                ([0, 0.], True),
                ([0, -1.], False),
                ([0., 0], True),
                ([0., -1], False),
                
                # number and string
                ([0, '0'], False),
                
                # strings
                (['', ''], True),
                (['', 'bobo'], False),
                (['bobo', 'bobo'], True),
            
            ),
            
            
            ('gt', 'le'): (
                
                # booleans
                ([False, False], False),
                ([False, True], False),
                ([True, False], True),
                ([True, True], False),
                
                # numbers
                ([0, 0], False),
                ([0, 1.], False),
                ([1., 0.], True),
                ([1., -1], True),
                
                # strings
                (['', ''], False),
                (['x', ''], True),
                (['x', 'x'], False),
                (['x', 'y'], False),
                (['y', 'x'], True),
                (['x', 'bobo'], True),
                
            ),
        
        
            ('ge', 'lt'): (
                
                # booleans
                ([False, False], True),
                ([False, True], False),
                ([True, False], True),
                ([True, True], True),
                
                # numbers
                ([0, 0], True),
                ([0, 1.], False),
                ([1., 0.], True),
                ([1., -1], True),
                
                # strings
                (['', ''], True),
                (['x', ''], True),
                (['x', 'x'], True),
                (['x', 'y'], False),
                (['y', 'x'], True),
                (['x', 'bobo'], True),
                
            ),
        
        
        }
        
        for (op, complement), pairs in cases.items():
            # print(f'testing "{op}" and "{complement}" operators...')
            for initial_stack, expected in pairs:
                self._test_comparison(op, initial_stack, expected)
                self._test_comparison(complement, initial_stack, not expected)
    
    
    def _test_comparison(self, op, initial_stack, expected):
        self._set_up(initial_stack)
        c = self.calculator
        c.execute(op)
        actual = c.operand_stack.pop()
        self.assertEqual(actual, expected)
       

    def test_operand_count_and_type_errors(self):
        
        binary_arithmetic_stacks = (
            [],
            [0],
            [True, 0.],
            [False, 0],
            [0, '0'],
            ['0', '0'],
        )
        
        unary_arithmetic_stacks = (
            [],
            [True],
            [False],
            ['0'],
        )
        
        coercion_stacks = (
            [],
            [True],
            [False],
        )
        
        binary_logical_stacks = (
            [],
            [True],
            [0, True],
            [False, 0.],
            [False, 'True'],
            ['False', 'False'],
        )
        
        cases = {
            
            'dup': (
                [],
            ),
            
            'exch': (
                [],
                [0],
            ),
            
            'pop': (
                [],
            ),
            
            'add': binary_arithmetic_stacks,
            'sub': binary_arithmetic_stacks,
            'mul': binary_arithmetic_stacks,
            'div': binary_arithmetic_stacks,
            'mod': binary_arithmetic_stacks,
            'pow': binary_arithmetic_stacks,
            
            'neg': unary_arithmetic_stacks,
            'abs': unary_arithmetic_stacks,
            'ceiling': unary_arithmetic_stacks,
            'floor': unary_arithmetic_stacks,
            'round': unary_arithmetic_stacks,
            'exp': unary_arithmetic_stacks,
            'ln': unary_arithmetic_stacks,
            'log2': unary_arithmetic_stacks,
            'log10': unary_arithmetic_stacks,
            
            'boolean': coercion_stacks,
            'integer': coercion_stacks,
            'float': coercion_stacks,
            
            'and': binary_logical_stacks,
            'or': binary_logical_stacks,
            'xor': binary_logical_stacks,
            
            'not': (
                [],
                [0],
                [0.],
                ['False'],
            )
            
        }
        
        self._test_errors(cases)
    
    
    def _test_errors(self, cases):
        for operator_name, operand_stacks in cases.items():
            # print(f'testing "{operator_name}" operator errors...')
            for operand_stack in operand_stacks:
                self._set_up(operand_stack)
                self.assert_raises(
                    CalculatorError, self.calculator.execute, operator_name)
                self._assert_calculator(operand_stack)
    
    
    def test_operand_value_errors(self):
        
        divide_by_zero_stacks = ([1, 0],)
        log_domain_error_stacks = ([0], [-1])
        
        cases = {
            
            'div': divide_by_zero_stacks,
            'mod': divide_by_zero_stacks,
            
            'ln': log_domain_error_stacks,
            'log2': log_domain_error_stacks,
            'log10': log_domain_error_stacks,
            
            'boolean': (['0'], ['0.'], ['bobo']),
            'integer': (['0.'], ['bobo']),
            'float': (['bobo'],),
        
        }
        
        self._test_errors(cases)
    
    
    def test_load(self):
        
        c = self.calculator
        
        c.dict_stack.put('x', 0)
        c.dict_stack.put('y', 1)
        
        c.execute('x')
        x = c.operand_stack.pop()
        self.assertEqual(x, 0)
        
        c.execute('y')
        y = c.operand_stack.pop()
        self.assertEqual(y, 1)
    
    
    def test_expressions(self):
        
        cases = (
            (2, 'x 3 mul 1 add', 7),
            (2, '4 x mul 1 gt', True),
            (2, 'x 3 exch sub', 1),
            ('2.', 'x float 3 mul 6 eq', True),
        )
        
        c = self.calculator
        
        for x, code, result in cases:
            c.clear()
            c.dict_stack.put('x', x)
            c.execute(code)
            self._assert_calculator([result], [('x', x)])
    
    
    def _set_up(self, operand_stack=[], bindings=[]):
        
        c = self.calculator
        
        c.clear()
        
        if not isinstance(operand_stack, list):
            operand_stack = [operand_stack]
            
        for obj in operand_stack:
            c.operand_stack.push(obj)
            
        for binding in bindings:
            c.dict_stack.store(*binding)
    
    
    def _assert_calculator(self, operand_stack, bindings=[]):
        
        c = self.calculator
        
        # Get operand stack.
        stack = c.operand_stack
        size = len(stack)
        actual = stack.peek(size)
        
        if not isinstance(operand_stack, list):
            operand_stack = [operand_stack]
            
        self.assertEqual(actual, operand_stack)
        
        for name, expected in bindings:
            actual = c.dict_stack.get(name)
            self.assertEqual(actual, expected)
