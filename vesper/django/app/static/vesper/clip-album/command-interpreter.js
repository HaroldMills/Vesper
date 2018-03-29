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


/*

Improved Terminology

I'd like to rethink the terminology Vesper uses for processing keyboard
and mouse input. I'd like to make it more consistent with what other
programs (e.g. Atom, Visual Studio Code, and IntelliJ IDEA) use, while
also taking into consideration the Vesper context into which it must fit.

Terms:

* Command (or Action?) - A command offered by a UI item, like a clip album,
clip display, or clip view. A command has a textual representation that is
simultaneously human- and machine-readable. Ideally, I'd like to be able to
record all user interaction with UI elements in this form.

* Key, Key Combination, Key Sequence - I like the Atom terminology for
these things: see
https://flight-manual.atom.io/behind-atom/sections/keymaps-in-depth/

* Keybinding - A key sequence/command pair.

* Key

*/


/*
# A possible new grammar for key sequences:
#
# <key_sequence> :== <key_combination> | <key_combination> <key_sequence>
# <key_combination> :== <modifier_keys><character_or_special_key>
# <modifier_keys> :== "" | <modifier_key>+<modifier_keys>
# <modifier_key> :== Cmd | Ctrl | Alt | Shift
# <character_or_special_key> :== <character_key> | <special_key>
# <character_key> :== <letter> | <digit> | <symbol>
# <letter> :== ASCII letters
# <digit> :== ASCII digits
# <symbol> :== ASCII printable symbols
# <special_key> ::= ArrowDown | ArrowLeft | ArrowRight | ArrowUp | Backspace |
#     Delete | End | Enter | Escape | Home | PageDown | PageUp | Space | Tab
#
# Notes:
#
# * Users might want to avoid using modifier keys and special keys since
#   doing so may interfere with existing browser shortcuts. I would prefer
#   to let users decide that for themselves, however, rather than just
#   disallowing it.
#
# * Special key names are more or less from the standard set of web
#   browser keyboard event key values: see http://developer.mozilla.org/
#   en-US/docs/Web/API/KeyboardEvent/key/Key_Values. I chose to use "Space"
#   rather than " " since we use the space character as the separator in key
#   sequences. Aside from that consideration, I also think it's clearer.
#
# * The key sequence syntax was strongly influenced by Atom keymaps: see
#   https://flight-manual.atom.io/behind-atom/sections/keymaps-in-depth/.
#   I prefer camel case modifier key and special key names, however, and
#   "+" rather than "-" as the key combination separator.
#
# * Requiring that the keys of key sequences be separated by spaces
#   would mean that a key sequence that used to be specified as, say,
#   "ab" would instead have to be specified as "a b". The latter would
#   be less desirable all else being equal, but all else is not equal
#   since the separation allows the use of special key names.
#
# * I experimented with using dashes rather than underscores to separate
#   the components of interpreter command and variable names. I think
#   using dashes is not a good idea, though, since it might make it
#   more difficult in the future to add support for arithmetic to the
#   command language.
#
# * It's tempting to allow the invocation of a function without arguments
#   to be represented in key bindings by just the function name rather
#   than a list whose only element is the function name. I think that
#   would be problematic, however. We want to allow YAML specification
#   of sequences of function invocations, and loosening how zero-argument
#   function invocations are represented would make such specifications
#   ambiguous. For example, would "[a, b]" represent invocation of function
#   a on argument b, or invocation of function a followed by invocation of
#   function b, or possibly something else?
#
# * Command language functions currently cannot return values, and are
#   executed only for their side effects.

preset_metadata:
    name: Calls
    type: Clip Album Key Bindings
    documentation: Clip album key bindings for classifying calls to species.
    parents: []

Clip Album:

    interpreter_initialization: [
        [set_persistent_variable, annotation_name, Classification]
        [set_persistent_variable, annotation_scope, Selection]
    ]

    key_bindings:

        Space: [show_next_page]
        Shift+Space: [show_previous_page]
        PageDown: [show_next_page]
        PageUp: [show_previous_page]
        Tab: [select_next_clip]
        Shift+Tab: [select_previous_clip]
        ArrowRight: [select_next_clip]
        ArrowLeft: [select_previous_clip]

        ">": [show_next_page]
        "<": [show_previous_page]
        ".": [select_next_clip]
        ",": [select_previous_clip]
        "/": [play_selected_clip]
        "~": [toggle_clip_labels]

        "#": [set_temporary_variable, annotation_scope, Page]
        "\\": [clear_key_buffer_and_temporary_variables]

        A: [annotate_clips, Call.AMCO]
        "a p": [annotate_clips, Call.AMPI]
        i: [annotate_clips, Call.AMPI]
        r: [annotate_clips, Call.AMRE]
        R: [annotate_clips, Call.AMRO]
        a: [annotate_clips, Call.ATSP]
        Q: [annotate_clips, Call.BOBO]
        B: [annotate_clips, Call.BAIS]
        G: [annotate_clips, Call.BHGR]
        K: [annotate_clips, Call.CAWA]
        C: [annotate_clips, Call.CCSP_BRSP]
        c: [annotate_clips, Call.CHSP]
        y: [annotate_clips, Call.COYE]
        j: [annotate_clips, Call.DEJU]
        d: [annotate_clips, Call.DBUP]
        k: [annotate_clips, Call.GCKI]
        g: [annotate_clips, Call.GRSP]
        Y: [annotate_clips, Call.GRYE]
        E: [annotate_clips, Call.HETH]
        H: [annotate_clips, Call.HOLA]
        L: [annotate_clips, Call.LALO]
        b: [annotate_clips, Call.LAZB]
        l: [annotate_clips, Call.LBCU]
        I: [annotate_clips, Call.LISP]
        m: [annotate_clips, Call.MGWA]
        n: [annotate_clips, Call.NOWA]
        o: [annotate_clips, Call.OVEN]
        P: [annotate_clips, Call.PYNU_LBDO]
        p: [annotate_clips, Call.Peep]
        s: [annotate_clips, Call.SAVS]
        S: [annotate_clips, Call.SORA]
        Z: [annotate_clips, Call.SOSP]
        q: [annotate_clips, Call.SPSA_SOSA]
        h: [annotate_clips, Call.SWTH]
        u: [annotate_clips, Call.Unknown]
        U: [annotate_clips, Call.UPSA]
        e: [annotate_clips, Call.VEER]
        v: [annotate_clips, Call.VESP]
        V: [annotate_clips, Call.VIRA]
        W: [annotate_clips, Call.WCSP]
        t: [annotate_clips, Call.WETA]
        w: [annotate_clips, Call.WIWA]
        x: [annotate_clips, Call.Weak]
        X: [annotate_clips, Call.WTSP]
        T: [annotate_clips, Call.YRWA]
        z: [annotate_clips, Call.Zeep]

Time-Frequency Marker:

    key_bindings:
        m: [set_marker]
        c: [clear_marker]
*/


export class CommandInterpreter {


    static get COMMAND_UNRECOGNIZED() { return 0; }
    static get COMMAND_INCOMPLETE() { return 1; }
    static get COMMAND_COMPLETE() { return 2; }


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

        const commands = [
			['set-persistent-variable', ['name', 'value'],
				(a, e) => this._createPersistentVariable(e, ...a)],
			['delete-persistent-variable', ['name'],
                (a, e) => this._deletePersistentVariable(e, ...a)],
			['clear-persistent-variables', [],
                (a, e) => this._clearPersistentVariables(e, ...a)],
			['set-temporary-variable', ['name', 'value'],
                (a, e) => this._setTemporaryVariable(e, ...a)],
			['delete-temporary-variable', ['name'],
                (a, e) => this._deleteTemporaryVariable(e, ...a)],
			['clear-temporary-variables', [],
                (a, e) => this._clearTemporaryVariables(e, ...a)],
            ['clear-key-buffer', [],
                (a, e) => this._clearKeyBuffer(e, ...a)]
			['clear-key-buffer-and-temporary-variables', [],
				(a, e) => this._clearKeyBufferAndTemporaryBindings(e, ...a)]
		];

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
		];

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
//			'CommandInterpreter.handleKey', key,
//			this._commandNameBuffer);

		const name = this._commandNameBuffer + key;
		const action = this._commandActions.get(name);

		if (action !== undefined) {
			// `name` is a command name

			try {

			    this._executeCommand(name, action);

			} finally {

				// It is important to clear the command name buffer
				// whether or not the command throws an exception,
				// so the buffer is always empty when command
				// processing completes.
			    this._clearCommandNameBuffer();

			}

			return [CommandInterpreter.COMMAND_COMPLETE, name];

		} else if (this._commandNamePrefixes.has(name)) {
			// `name` is a proper prefix of one or more command names

			this._commandNameBuffer = name;
			return [CommandInterpreter.COMMAND_INCOMPLETE, name];

		} else {
			// `name` is not a prefix of any command name

			this._clearCommandNameBuffer();
			this._environment.clearLocals();
			return [CommandInterpreter.COMMAND_UNRECOGNIZED, name];

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
export class BuiltInFunction extends _Function {

	_execute(args, environment) {
		this._executionDelegate(args, environment);
	}

}


/*
 * A `RegularFunction` adds arguments to the local environment before
 * invoking the execution delegate, and clears the local environment after
 * the execution delegate completes.
 */
export class RegularFunction extends _Function {

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


export class Environment {


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


export class CompositeCommandInterpreter {


    constructor(interpreters) {
        this._interpreters = interpreters;
        this._activeInterpreter = null;
    }


    handleKey(key) {

        if (this._activeInterpreter === null) {
            // new command

            for (const interpreter of this._interpreters) {

                const [status, name] = interpreter.handleKey(key);

                if (status === CommandInterpreter.COMMAND_INCOMPLETE) {

                    this._activeInterpreter = interpreter;
                    return [CommandInterpreter.COMMAND_INCOMPLETE, name];

                } else if (status === CommandInterpreter.COMMAND_COMPLETE) {

                    return [CommandInterpreter.COMMAND_COMPLETE, name];

                }

            }

            return [CommandInterpreter.COMMAND_UNRECOGNIZED, key];

        } else {
            // new character of incomplete command

            const [status, name] = this._activeInterpreter.handleKey(key);

            if (status === CommandInterpreter.COMMAND_COMPLETE)
                this._activeInterpreter = null;

            return [status, name];

        }


    }


}
