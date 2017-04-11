'use strict'


/*

Terms:

* function
* environment
* variable
* global environment
* local environment
* action - function and arguments
* command - name and action

*/


/*

globals:
    annotation_name: Classification
    annotation_scope: Selected
    
commands:

    "\": [clear_command_and_locals]
    
    ">": [show_next_page]
    "<": [show_previous_page]
    ".": [select_next_clip]
    ",": [select_previous_clip]
    "/": [play_selected_clip]
    
    "#": [set_local, annotation_scope, Page]
    "*": [set_local, annotation_scope, All]

    c: [annotate_clips, Call]
    C: [annotate_page_clips, Call]
    n: [annotate_clips, Noise]
    N: [annotate_page_clips, Noise]
    x: [unannotate_clips]
    X: [unannotate_page_clips]
    
    r: [tag_clips, Review]
    u: [untag_clips]

*/


class KeyboardCommandInterpreter {
	
	
	constructor(spec, functions) {
		
		this._functions = this._getFunctions(functions);
		
		this._environment = new Environment();
		this._initGlobals(spec);
		
		this._commandActions = this._getCommandActions(spec);
		this._commandNamePrefixes = this._getCommandNamePrefixes();

		this._clearCommandNameBuffer();
		
	}
	
	
	_getFunctions(functionList) {
		const builtInFunctions = this._createBuiltInFunctions();
		const functions = functionList.map((f) => [f.name, f]);
		return new Map([...builtInFunctions, ...functions]);
	}
		
		
	_createBuiltInFunctions() {
		
		const functionData = [
			['set_global', ['name', 'value'],
				(a, e) => this._setGlobal(e, ...a)],
			['delete_global', ['name'], (a, e) => this._deleteGlobal(e, ...a)],
			['clear_globals', [], (a, e) => this._clearGlobals(e, ...a)],
			['set_local', ['name', 'value'], (a, e) => this._setLocal(e, ...a)],
			['delete_local', ['name'], (a, e) => this._deleteLocal(e, ...a)],
			['clear_locals', [], (a, e) => this._clearLocals(e, ...a)],
			['clear_command_and_locals', [],
				(a, e) => this._clearCommandAndLocals(e, ...a)]
		]
		
		const entries = functionData.map(this._createBuiltInFunctionEntry);
		return new Map(entries);
		
	}
	
	
	_createBuiltInFunctionEntry(functionData) {
		const name = functionData[0];
		const value = new BuiltInFunction(...functionData);
		return [name, value];
	}

	
	_setGlobal(environment, name, value) {
		environment.setGlobal(name, value);
	}
	
	
	_deleteGlobal(environment, name) {
		environment.deleteGlobal(name);
	}
	
	
	_clearGlobals(environment) {
		environment.clearGlobals();
	}
	
	
	_setLocal(environment, name, value) {
		environment.setLocal(name, value);
	}
	
	
	_deleteLocal(environment, name) {
		environment.deleteLocal(name);
	}
	
	
	_clearLocals(environment) {
		environment.clearLocals();
	}
	
	
	_clearCommandAndLocals(environment) {
		this._clearCommandNameBuffer();
		environment.clearLocals();
	}
	
	
	_initGlobals(spec) {
		
		if (spec.globals !== undefined) {
			
			for (const name of Object.keys(spec.globals)) {
				const value = spec.globals[name];
				this._environment.setGlobal(name, value);
			}
			
		}
		
	}
	
	
	_getCommandActions(spec) {
		
		const actions = new Map();
		
		if (spec.commands !== undefined)
			for (const name of Object.keys(spec.commands)) {
				actions.set(name, spec.commands[name]);
			}
		
		return actions;
		
	}
	
	
	// Gets the set of all proper prefixes of this interpreter's command names.
	_getCommandNamePrefixes() {
		
		const prefixes = new Set();
		
		for (const name of this._commandActions.keys())
			for (let i = 1; i < name.length; i++)
				prefixes.add(name.slice(0, i));
	
	    return prefixes;
	    
	}
	
	
	_clearCommandNameBuffer() {
		this._commandNameBuffer = '';
	}
	
	
	handleKey(key) {
		
//		console.log(
//			'KeyboardCommandInterpreter.handleKey', key,
//			this._commandNameBuffer);
		
		const name = this._commandNameBuffer + key;
		const action = this._commandActions.get(name);
		
		if (action !== undefined) {
			// `name` is a command name
			
			this._executeCommand(name, action);
			this._clearCommandNameBuffer();
			
		} else if (this._commandNamePrefixes.has(name)) {
			// `name` is a proper prefix of one or more command names
			
			this._commandNameBuffer = name;
			
		} else {
			// `name` is not a prefix of any command name
			
			this._clearCommandNameBuffer();
			this._environment.clearLocals();
			throw new Error(`Unrecognized command name "${name}".`);
			
		}
				
	}
	
	
	_executeCommand(command_name, action) {
		
		const function_name = action[0];
		const function_ = this._functions.get(function_name);
		
		if (function_ !== undefined) {
			
			const function_arguments = action.slice(1);
			
			try {
				
			    function_.execute(function_arguments, this._environment);
		
			} catch (e) {
				
				throw new Error(
		        	`Execution of command "${command_name}" failed with ` +
		        	`message: ${e.message}`);
		        
			}
			
		} else {
			
			throw new Error(
				`Could not find function "${function_name}" for ` +
				`command "${command_name}".`);
			
		}

	}
	
	
}


class _Function {
	

	constructor(name, parameterNames, executionDelegate) {
		this._name = name;
		this._parameterNames = parameterNames;
		this._executionDelegate = executionDelegate;
	}
	
	
	get name() {
		return this._name;
	}
	
	
	get parameterNames() {
		return this._parameterNames;
	}
	
	
	get executionDelegate() {
		return this._executionDelegate;
	}


	execute(args, environment) {
		this._checkArguments(args);
		this._execute(args, environment);
	}
	
	
	_checkArguments(args) {
		
		const numRequiredArgs = this.parameterNames.length;
		
		if (args.length !== numRequiredArgs) {
			
			const suffix = numRequiredArgs === 1 ? '' : 's';
			
			throw new Error(
				`Function "${this.name}" requires ${numRequiredArgs} ` +
				`argument${suffix} but received ${args.length}.`);
			
		}
		
	}

	
	_execute(args, environment) {
		throw new Error('The "_execute" method is not implemented.');
	}
	
	
}


/*
 * A `BuiltInFunction` simply invokes its execution delegate. It does not
 * manipulate the local environment itself: any such manipulation is left
 * to the delegate.
 */
class BuiltInFunction extends _Function {
	
	_execute(args, environment) {
		this._executionDelegate(args, environment);
	}
	
}


/*
 * A `RegularFunction` adds arguments to the local environment before
 * invoking the execution delegate, and clears the local environment after
 * the execution delegate completes.
 */
class RegularFunction extends _Function {
	
	_execute(args, environment) {
		
		// Add arguments to local variables.
		for (const [i, name] of this.parameterNames.entries())
			environment.setLocal(name, args[i]);
		
		try {
			
		    this._executionDelegate(environment);
					
		} finally {
		
		    // Clear local variables. Note that this includes *all* local
			// variables, such as any that may have been set via the
			// `set_local` function, not just the arguments of
			// this function.
		    environment.clearLocals();
		    
		}
		
	}

}


class Environment {
	
	
	constructor() {
		this._globals = new Map();
		this._locals = new Map();
	}
	
	
    setGlobal(name, value) {
    	this._globals.set(name, value);
    }
    
    
    deleteGlobal(name) {
    	delete this._globals.delete(name);
    }
    
    
    clearGlobals() {
    	this._globals.clear();
    }
    
    
    setLocal(name, value) {
    	this._locals.set(name, value);
    }
    
    
    deleteLocal(name) {
    	delete this._locals.delete(name);
    }
    
    
    clearLocals() {
    	this._locals.clear();
    }
    
    
    get(name) {
    	
        let value = this._locals.get(name);
    	if (value !== undefined)
    		return value;
    	
    	value = this._globals.get(name);
        if (value !== undefined)
    		return value;
    	    
        return undefined;
    	    
    }
    
    
    getRequired(name) {
    	
    	const value = this.get(name);
    	
    	if (value === undefined)
    		throw new Error(
    			`Required command interpreter variable "${name}" not found.`);
    	
    	else
    	    return value;
    	
    }
	
	
}
