'use strict'


describe('Environment class', () => {
	
	
	it('globals', () => {
		
		const e = new Environment();
		const expectValue = (name, value) => expect(e.get(name)).toBe(value);
		const expectUndefined = name => expectValue(name, undefined);
		
		e.setGlobal('one', 1);
		e.setGlobal('two', 2);
		e.setGlobal('three', 3);
		
		expectValue('one', 1);
		expectValue('two', 2);
		expectValue('three', 3);
		
		e.deleteGlobal('two');
		
		expectValue('one', 1)
		expectUndefined('two');
		expectValue('three', 3);
		
		e.clearLocals();
		
		expectValue('one', 1);
		expectValue('three', 3);
		
		e.clearGlobals();
		
		expectUndefined('one');
		expectUndefined('three');
		
	});
	
	
	it('locals', () => {
		
		const e = new Environment();
		const expectValue = (name, value) => expect(e.get(name)).toBe(value);
		const expectUndefined = name => expectValue(name, undefined);
		
		e.setLocal('one', 1);
		e.setLocal('two', 2);
		e.setLocal('three', 3);
		
		expectValue('one', 1);
		expectValue('two', 2);
		expectValue('three', 3);
		
		e.deleteLocal('two');
		
		expectValue('one', 1)
		expectUndefined('two');
		expectValue('three', 3);
		
		e.clearGlobals();
		
		expectValue('one', 1);
		expectValue('three', 3);
		
		e.clearLocals();
		
		expectUndefined('one');
		expectUndefined('three');
		
	});
	
	
	it('globals and locals', () => {
		
		const e = new Environment();
		const expectValue = (name, value) => expect(e.get(name)).toBe(value);
		const expectUndefined = name => expectValue(name, undefined);
		
		e.setGlobal('one', 1);
		e.setGlobal('two', 2);
		e.setLocal('three', 3);
		e.setLocal('four', 4);
		
		expectValue('one', 1);
		expectValue('two', 2);
		expectValue('three', 3);
		expectValue('four', 4);
        
        e.clearLocals();

        expectValue('one', 1);
        expectValue('two', 2);
        expectUndefined('three');
        expectUndefined('four');
        
		e.setLocal('three', 3);
		e.setLocal('four', 4);
		e.clearGlobals();
		
		expectUndefined('one');
		expectUndefined('two');
		expectValue('three', 3);
		expectValue('four', 4);
		
	});
	

});


describe('InterpreterFunction class', () => {
	
	
	it('construction and execution', () => {
		
		function setLocal(environment, name, value) {
			environment.setLocal(name, value);
		}
		
		const f = new InterpreterFunction(
			'set_local', ['name', 'value'], setLocal);
		
		const e = new Environment();
		
		expect(f.name).toBe('set_local');
		expect(f.argumentNames).toEqual(['name', 'value']);
		expect(f.executionDelegate).toBe(setLocal);
		
		f.execute(['bobo', 1], e);
		
		expect(e.get('bobo')).toBe(1);
		
	});
	
	
});


describe('ContributedFunction class', () => {
	
	
	it('construction and execution', () => {
		
		function setGlobal(environment) {
			const name = environment.get('name');
			const value = environment.get('value');
			environment.setGlobal(name, value);
		}
		
		const f = new ContributedFunction(
			'set_global', ['name', 'value'], setGlobal);
		
		const e = new Environment();
		
		expect(f.name).toBe('set_global');
		expect(f.argumentNames).toEqual(['name', 'value']);
		expect(f.executionDelegate).toBe(setGlobal);
		
		e.setLocal('local', 1);
		f.execute(['bobo', 2], e);
		
		expect(e.get('local')).toBe(undefined);
		expect(e.get('bobo')).toBe(2);
		
	});
	
	
});


describe('KeyboardCommandInterpreter class', () => {
	
	
	it('interpreter functions', () => {
		
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
				
		const interpreter = new KeyboardCommandInterpreter(spec, functions);
		const environment = interpreter._environment;
		
		function input(command) {
			for (const c of command)
				interpreter.onKey(c);
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
	
	
	it('contributed functions', () => {
		
		const spec = {
			
			'commands': {
				's1': ['set', 'one', 1],
				's2': ['set', 'two', 2],
				's3': ['set_three'],
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
			new ContributedFunction('set', ['name', 'value'], set),
			new ContributedFunction('set_three', ['value'], set)
		];
				
		const interpreter = new KeyboardCommandInterpreter(spec, functions);
		const environment = interpreter._environment;
		
		function input(command) {
			for (const c of command)
				interpreter.onKey(c);
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
