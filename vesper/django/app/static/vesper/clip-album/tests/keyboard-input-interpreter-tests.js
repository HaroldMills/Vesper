import { CommandableDelegate, Environment, KeyboardInputInterpreter }
    from '../keyboard-input-interpreter.js';


function _input(command, interpreter, specialKey = null) {
    let i = 0;
    for (const c of command) {
        const [status, name] = interpreter.handleKey(c);
        if (c === specialKey) {
            expect(status).toBe(
                KeyboardInputInterpreter.KEY_SEQUENCE_COMPLETE);
            expect(name).toBe(c);
        } else {
            const expectedStatus =
                i === command.length - 1 ?
                KeyboardInputInterpreter.KEY_SEQUENCE_COMPLETE :
                KeyboardInputInterpreter.KEY_SEQUENCE_PARTIAL;
            expect(status).toBe(expectedStatus);
            const expectedName =
                command[command.length - 1] === specialKey ?
                specialKey :
                command.slice(0, i + 1);
            expect(name).toBe(command.slice(0, i + 1));
            i += 1;
        }
    }
}


describe('Environment', () => {


	it('persistent variables', () => {

		const e = new Environment();

		function expectValue(name, value) {
			expect(e.get(name)).toBe(value);
			expect(e.getRequired(name)).toBe(value);
		}

		function expectUndefined(name) {
			expect(e.get(name)).toBe(undefined);
			expect(() => e.getRequired(name)).toThrowError(Error);
		}

		e.setPersistentVariable('one', 1);
		e.setPersistentVariable('two', 2);
		e.setPersistentVariable('three', 3);

		expectValue('one', 1);
		expectValue('two', 2);
		expectValue('three', 3);

		e.deletePersistentVariable('two');

		expectValue('one', 1)
		expectUndefined('two');
		expectValue('three', 3);

		e.clearTemporaryVariables();

		expectValue('one', 1);
		expectValue('three', 3);

		e.clearPersistentVariables();

		expectUndefined('one');
		expectUndefined('three');

	});


	it('temporary variables', () => {

		const e = new Environment();
		const expectValue = (name, value) => expect(e.get(name)).toBe(value);
		const expectUndefined = name => expectValue(name, undefined);

		e.setTemporaryVariable('one', 1);
		e.setTemporaryVariable('two', 2);
		e.setTemporaryVariable('three', 3);

		expectValue('one', 1);
		expectValue('two', 2);
		expectValue('three', 3);

		e.deleteTemporaryVariable('two');

		expectValue('one', 1)
		expectUndefined('two');
		expectValue('three', 3);

		e.clearPersistentVariables();

		expectValue('one', 1);
		expectValue('three', 3);

		e.clearTemporaryVariables();

		expectUndefined('one');
		expectUndefined('three');

	});


	it('persistent and temporary variables', () => {

		const e = new Environment();
		const expectValue = (name, value) => expect(e.get(name)).toBe(value);
		const expectUndefined = name => expectValue(name, undefined);

		e.setPersistentVariable('one', 1);
		e.setPersistentVariable('two', 2);
		e.setTemporaryVariable('three', 3);
		e.setTemporaryVariable('four', 4);

		expectValue('one', 1);
		expectValue('two', 2);
		expectValue('three', 3);
		expectValue('four', 4);

        e.clearTemporaryVariables();

        expectValue('one', 1);
        expectValue('two', 2);
        expectUndefined('three');
        expectUndefined('four');

		e.setTemporaryVariable('three', 3);
		e.setTemporaryVariable('four', 4);
		e.clearPersistentVariables();

		expectUndefined('one');
		expectUndefined('two');
		expectValue('three', 3);
		expectValue('four', 4);

	});


});


describe('KeyboardInputInterpreter', () => {


    // interpreter initialization
    // interpreter commands
    // special keys
    // single commandable
    // multiple commandables
    // settings updates


    it ('interpreter initialization', () => {

        const settings = {

            'interpreterInitializationCommands': [
                ['set_persistent_variable', 'one', 1],
                ['set_temporary_variable', 'two', 2]
            ],

            'keyBindings': {}

        };

        const interpreter = new KeyboardInputInterpreter(settings);
        const environment = interpreter._environment;

        const expectValue = (name, value) =>
            expect(environment.get(name)).toBe(value);

        expectValue('one', 1);
        expectValue('two', 2);

    });


    it ('interpreter commands', () => {

        const settings = {
            'keyBindings': {
                'Keyboard Input Interpreter': {
                    'sp1': ['set_persistent_variable', 'one', 1],
                    'st2': ['set_temporary_variable', 'two', 2]
                }
            }
        };

        const interpreter = new KeyboardInputInterpreter(settings);
        const environment = interpreter._environment;

        const input = command => _input(command, interpreter);
        const expectValue = (name, value) =>
            expect(environment.get(name)).toBe(value);

        input('sp1');
        input('st2');

        expectValue('one', 1);
        expectValue('two', 2);

    });


    it ('default special keys', () => {

        const settings = {
            'keyBindings': {
                'Keyboard Input Interpreter': {
                    'sp1': ['set_persistent_variable', 'one', 1],
                }
            }
        };

        const interpreter = new KeyboardInputInterpreter(settings);
        const environment = interpreter._environment;

        const input = command => _input(command, interpreter, '\\');
        const expectValue = (name, value) =>
            expect(environment.get(name)).toBe(value);
        const expectUndefined = name => expectValue(name, undefined);

        input('\\');
        expectUndefined('one');

        input('s\\');
        expectUndefined('one');

        input('sp\\');
        expectUndefined('one');

        input('sp1');
        expectValue('one', 1);

    });


    it ('non-default special keys', () => {

        const settings = {
            'keyBindings': {
                'Special': {
                    '/': ['clear_key_buffer_and_temporary_variables']
                },
                'Keyboard Input Interpreter': {
                    'sp1': ['set_persistent_variable', 'one', 1],
                }
            }
        };

        const interpreter = new KeyboardInputInterpreter(settings);
        const environment = interpreter._environment;

        const input = command => _input(command, interpreter, '/');
        const expectValue = (name, value) =>
            expect(environment.get(name)).toBe(value);
        const expectUndefined = name => expectValue(name, undefined);

        input('/');
        expectUndefined('one');

        input('s/');
        expectUndefined('one');

        input('sp/');
        expectUndefined('one');

        input('sp1');
        expectValue('one', 1);

    });


    it ('single commandable', () => {

        const settings = {
            'keyBindings': {
                'Commandable': {
                    'sp1': ['set_persistent_variable', 'one', 1],
                    'st2': ['set_temporary_variable', 'two', 2],
                    'sx3': ['set_x', 3]
                }
            }
        };

        const interpreter = new KeyboardInputInterpreter(settings);
        const environment = interpreter._environment;

        const commandable = new _Commandable('Commandable')
        interpreter.pushCommandable(commandable);

        const input = command => _input(command, interpreter);
        const expectValue = (name, value) =>
            expect(environment.get(name)).toBe(value);

        input('sp1');
        input('st2');

        expectValue('one', 1);
        expectValue('two', 2);

        input('sx3');
        expect(commandable.x).toBe(3);

    });


    it ('two commandables', () => {

        const settings = {
            'keyBindings': {
                'Keyboard Input Interpreter': {
                    'sp0': ['set_persistent_variable', 'zero', 0]
                },
                'Commandable 1': {
                    'sp1': ['set_persistent_variable', 'one', 1],
                    'sx3': ['set_x', 3]
                },
                'Commandable 2': {
                    'st2': ['set_temporary_variable', 'two', 2],
                    'sx4': ['set_x', 4]
                }
            }
        };

        const interpreter = new KeyboardInputInterpreter(settings);
        const environment = interpreter._environment;

        const commandable_1 = new _Commandable('Commandable 1')
        interpreter.pushCommandable(commandable_1);

        const commandable_2 = new _Commandable('Commandable 2')
        interpreter.pushCommandable(commandable_2);

        const input = command => _input(command, interpreter);
        const expectValue = (name, value) =>
            expect(environment.get(name)).toBe(value);

        input('sp0');
        input('sp1');
        input('st2');

        expectValue('zero', 0);
        expectValue('one', 1);
        expectValue('two', 2);

        input('sx3');
        expect(commandable_1.x).toBe(3);

        input('sx4');
        expect(commandable_2.x).toBe(4);

    });


    it ('settings updates', () => {

        const settings = {
            'globals': {
                'zero': 0,
            },
            'commands': {
                'sx1': ['set_x', 1]
            }
        }

        const interpreter = new KeyboardInputInterpreter(settings);
        const environment = interpreter._environment;

        const commandable = new _Commandable('Clip Album')
        interpreter.pushCommandable(commandable);

        const input = command => _input(command, interpreter);
        const expectValue = (name, value) =>
            expect(environment.get(name)).toBe(value);

        expectValue('zero', 0);

        input('sx1');
        expect(commandable.x).toBe(1);

    });


});


const _COMMAND_SPECS = [
    ['set_x', 'value']
];


const _commandableDelegate = new CommandableDelegate(_COMMAND_SPECS);


class _Commandable {


    constructor(commandableName) {
        this._commandableName = commandableName;
        this._commandableDelegate = _commandableDelegate;
        this._x = 0;
    }


    get commandableName() {
        return this._commandableName;
    }


    get x() {
        return this._x;
    }


    set x(value) {
        this._x = value;
    }


    hasCommand(commandName) {
        return this._commandableDelegate.hasCommand(commandName);
    }


    executeCommand(command, env) {
        return this._commandableDelegate.executeCommand(
            command, this, env);
    }


    _executeSetXCommand(env) {
        this.x = env.get('value');
    }


}


/*
describe('CommandInterpreter', () => {


	it('built-in functions', () => {

		const spec = {

			'commands': {

				'sg1': ['set_global', 'one', 1],
				'sg2': ['set_global', 'two', 2],
				'dg1': ['delete_global', 'one'],
				'dg2': ['delete_global', 'two'],
				'cg': ['clear_globals'],

				'sl2': ['set_local', 'two', 2],
				'sl3': ['set_local', 'three', 3],
				'dl2': ['delete_local', 'two'],
				'dl3': ['delete_local', 'three'],
				'cl': ['clear_locals']

			}

		};

		const functions = [];

		const interpreter = new CommandInterpreter(spec, functions);
		const environment = interpreter._environment;

		function input(command) {
			let i = 0;
			for (const c of command) {
				const [status, name] = interpreter.handleKey(c);
				const expectedStatus =
				    i === command.length - 1 ?
					CommandInterpreter.COMMAND_COMPLETE :
					CommandInterpreter.COMMAND_INCOMPLETE;
				expect(status).toBe(expectedStatus);
				expect(name).toBe(command.slice(0, i + 1));
				i += 1;
			}
		}

		function expectValue(name, value) {
			expect(environment.get(name)).toBe(value);
		}

		function expectUndefined(name) {
			expectValue(name, undefined);
		}


		// globals

		input('sg1');
		input('sg2');

		expectValue('one', 1);
		expectValue('two', 2);

		input('dg1');

		expectUndefined('one');
		expectValue('two', 2);

		input('sg1');

		expectValue('one', 1);
		expectValue('two', 2);

		input('cg');

		expectUndefined('one');
		expectUndefined('two');


		// locals

		input('sl2');
		input('sl3');

		expectValue('two', 2);
		expectValue('three', 3);

		input('dl2');

		expectUndefined('two');
		expectValue('three', 3);

		input('sl2');

		expectValue('two', 2);
		expectValue('three', 3);

		input('cl');

		expectUndefined('two');
		expectUndefined('three');


		// globals and locals

		input('sg1');
		input('sg2');
		input('sl2');
		input('sl3');

		expectValue('one', 1);
		expectValue('two', 2);
		expectValue('three', 3);

		input('cl');

		expectValue('one', 1);
		expectValue('two', 2);
		expectUndefined('three');


	});


	it('regular functions', () => {

		const spec = {

			'commands': {
				's1': ['set', 'one', 1],
				's2': ['set', 'two', 2],
				's3': ['set_three', 3],
			    'sl4': ['set_local', 'four', 4],
			    'sg5': ['set_global', 'five', 5]
			},

		    'globals': {
		    	'name': 'three',
		    },

		};

		const values = new Map();

		function set(environment) {
			const name = environment.get('name');
			const value = environment.get('value');
			values.set(name, value);
		}

		const functions = [
			new RegularFunction('set', ['name', 'value'], e => set(e)),
			new RegularFunction('set_three', ['value'], e => set(e))
		];

		const interpreter = new CommandInterpreter(spec, functions);
		const environment = interpreter._environment;

		function input(command) {
			let i = 0;
			for (const c of command) {
				const [status, name] = interpreter.handleKey(c);
				const expectedStatus =
				    i === command.length - 1 ?
					CommandInterpreter.COMMAND_COMPLETE :
					CommandInterpreter.COMMAND_INCOMPLETE;
				expect(status).toBe(expectedStatus);
				expect(name).toBe(command.slice(0, i + 1));
				i += 1;
			}
		}

		function expectSetValue(name, value) {
			expect(values.get(name) === value);
		}

		function expectValue(name, value) {
			expect(environment.get(name)).toBe(value);
		}

		function expectUndefined(name) {
			expectValue(name, undefined);
		}

		function expectEnv() {
			expectUndefined('one');
			expectUndefined('two');
			expectUndefined('three');
			expectUndefined('four');
			expectValue('five', 5);
			expectValue('name', 'three');
			expectUndefined('value');
		}

		input('sl4');
		input('sg5');

		input('s1');
		expectSetValue('one', 1);
		expectEnv();

		input('s2');
		expectSetValue('one', 1);
		expectSetValue('two', 2);
		expectEnv();

		input('s3');
		expectSetValue('one', 1);
		expectSetValue('two', 2);
		expectSetValue('three', 3);
		expectEnv();

	});


});
*/
/*
describe('CompositeCommandInterpreter', () => {


	it('handleKey', () => {

        let message = null;

		const functions = [
			new RegularFunction(
				'set_message', ['interpreterName', 'commandName'], e => {
					const iName = e.getRequired('interpreterName');
					const cName = e.getRequired('commandName');
					message = `${iName} executed command ${cName}`;
				}
			)
		];

		const specA = {
			'commands': {
				'a': ['set_message', 'A', 'a'],
				'mula': ['set_message', 'A', 'mula']
			}
		};

		const specB = {
			'commands': {
				'b': ['set_message', 'B', 'b'],
				'mulb': ['set_message', 'B', 'mulb']
			}
		};

		const a = new CommandInterpreter(specA, functions);
		const b = new CommandInterpreter(specB, functions);
		const c = new CompositeCommandInterpreter([a, b]);

        function input(interpreter, command) {
			let status, name;
			for (const c of command) {
				[status, name] = interpreter.handleKey(c);
				if (status === CommandInterpreter.COMMAND_UNRECOGNIZED)
				    return status;
			}
			return status;
		}

        function test(interpreter, command, expectedStatus, expectedMessage) {
			const status = input(interpreter, command);
			expect(status).toBe(expectedStatus);
			if (status === CommandInterpreter.COMMAND_COMPLETED)
			    expect(message).toBe(expectedMessage);
		}

		const completed = CommandInterpreter.COMMAND_COMPLETE;
		const unrecognized = CommandInterpreter.COMMAND_UNRECOGNIZED;

        test(c, 'a', completed, 'A executed command "a".');
		test(c, 'b', completed, 'B executed command "b".');
		test(c, 'mula', completed, 'A executed command "mula".');
		test(c, 'mulb', unrecognized, '');

	});


});
*/
