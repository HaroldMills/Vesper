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

    "_": [clear_command_and_locals]
    
    ">": [show_next_page]
    "<": [show_previous_page]
    "^": [select_first_clip]
    ".": [select_next_clip]
    ",": [select_previous_clip]
    "/": [play_selected_clip]
    
    "#": [set_local, scope, Page]
    "*": [set_local, scope, All]

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
	
	
	constructor(spec, contributedFunctions) {
		
		this._functions = this._getFunctions(contributedFunctions);
		
		this._environment = new Environment();
		this._initGlobals(spec);
		
		this._commandActions = this._getCommandActions(spec);
		this._commandNamePrefixes = this._getCommandNamePrefixes();

		this._clearCommandNameBuffer();
		
	}
	
	
	_getFunctions(contributedFunctions) {
		const interpreterFunctions = this._createInterpreterFunctions();
		contributedFunctions = contributedFunctions.map((f) => [f.name, f]);
		return new Map([...interpreterFunctions, ...contributedFunctions]);
	}
		
		
	_createInterpreterFunctions() {
		
		const functionData = [
			['set_global', ['name', 'value'], this._setGlobal],
			['delete_global', ['name'], this._deleteGlobal],
			['clear_globals', [], this._clearGlobals],
			['set_local', ['name', 'value'], this._setLocal],
			['delete_local', ['name'], this._deleteLocal],
			['clear_locals', [], this._clearLocals],
			['clear_command_and_locals', [], this._clearCommandAndLocals]
		]
		
		const entries = functionData.map(this._createInterpreterFunctionEntry);
		return new Map(entries);
		
	}
	
	
	_createInterpreterFunctionEntry(functionData) {
		const name = functionData[0];
		const value = new InterpreterFunction(...functionData);
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
		
		if (spec.globals) {
			
			for (const name of Object.keys(spec.globals)) {
				const value = spec.globals[name];
				this._environment.setGlobal(name, value);
			}
			
		}
		
	}
	
	
	_getCommandActions(spec) {
		
		const actions = new Map();
		
		if (spec.commands)
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
	
	
	onKey(key) {
		
		console.log('onKey', key, this._commandNameBuffer);
		
		const name = this._commandNameBuffer + key;
		const action = this._commandActions.get(name);
		
		if (action) {
			// `name` is a command name
			
			this._executeCommand(name, action);
			this._clearCommandNameBuffer();
			
		} else if (this._commandNamePrefixes.has(name)) {
			// `name` is a proper prefix of one or more command names
			
			this._commandNameBuffer = name;
			
		} else {
			// `name` is not a prefix of any command name
			
			// TODO: Notify user of error.
			console.log(`Unrecognized command name "${name}".`);
			this._clearCommandNameBuffer();
			
		}
				
	}
	
	
	_executeCommand(name, action) {
		
		const function_name = action[0];
		const function_arguments = action.slice(1);
		
		const function_ = this._functions.get(function_name);
		
		if (function_) {
			
			try {
				
			    function_.execute(function_arguments, this._environment);
		
			} catch (e) {
				
		        // TODO: Notify user of error.
		        console.log(
		        	`Execution of command "${name}" failed with ` +
		        	`message: ${e.message}`);
		        
			}
			
		} else {
			
			// TODO: Notify user of error.
			console.log(
				`Could not find function "${function_name}" for ` +
				`command "${name}".`);
			
		}

	}
	
	
}


class _Function {
	

	constructor(name, argumentNames, executionDelegate) {
		this._name = name;
		this._argumentNames = argumentNames;
		this._executionDelegate = executionDelegate;
	}
	
	
	get name() {
		return this._name;
	}
	
	
	get argumentNames() {
		return this._argumentNames;
	}
	
	
	get executionDelegate() {
		return this._executionDelegate;
	}


	execute(argumentValues, environment) {
		this._checkArguments(argumentValues);
		this._execute(argumentValues, environment);
	}
	
	
	_checkArguments(argumentValues) {
		
		const numArgs = this.argumentNames.length;
		
		if (argumentValues.length !== numArgs)
			throw new Error(
				`Function "${this.name}" requires ${numArgs} ` +
				`arguments but received ${argumentValues.length}.`);
		
	}

	
	_execute(argumentValues, environment) {
		throw Error('The "_execute" method is not implemented.');
	}
	
	
}


/*
 * An `InterpreterFunction` simply invokes its execution delegate.
 * It does not manipulate the local environment itself: any such
 * manipulation is left to the delegate.
 */
class InterpreterFunction extends _Function {
	
	_execute(argumentValues, environment) {
		this._executionDelegate(environment, ...argumentValues);
	}
	
}


/*
 * A `ContributedFunction` adds arguments to the local environment before
 * invoking the execution delegate, and clears the local environment after
 * the execution delegate completes.
 */
class ContributedFunction extends _Function {
	
	_execute(argumentValues, environment) {
		
		// Add arguments to local variables.
		for (const [i, name] of this.argumentNames.entries())
			environment.setLocal(name, argumentValues[i]);
		
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
	
	
}
