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

* Command - A command offered by a UI item, like a clip album,
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

interpreter_initialization_commands: [
    [set_persistent_variable, annotation_name, Classification]
    [set_persistent_variable, annotation_scope, Selection]
]


key_bindings:

    Special:
        "\\": [clear_key_buffer_and_temporary_variables]

    Clip Album:

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

    Spectrogram Time-Frequency Marker:
        m: [set_marker]
        c: [clear_marker]

*/

/*

New keyboard input interpreter design.

The key_bindings section of a Clip Album Key Bindings preset has
sections for different *commandables*, where a commandable is either
a UI component (e.g. a clip album, clip view, or clip view overlay)
or the keyboard input interpreter itself. Note that a commandable is
an *object* rather than a *class*. Each commandable has a name with
which its key bindings are labelled. The names of the keyboard input
interpreter and clip album are "Keyboard Input Interpreter" and
"Clip Album", and the names of the clip view and its overlays are
specified in the Clip Album Settings preset with the UI component
hierarchy.

The keyboard input interpreter maintains a stack of commandables
that is updated as the mouse moves. The interpreter is always at
the bottom of the stack, and above it are the commandable UI
components that are currently under the mouse, beginning with the
clip album

When a key is pressed, the keyboard input interpreter looks up the
current key sequence in the key bindings from the top of the stack
to the bottom. If it finds a binding that matches the key sequence,
it executes the bound command. The command must be supported either
by the UI component for which it was found or by the interpreter
itself.

Commands are implemented as instance methods of commandable classes.
The names of the methods are derived from the names of the commands.
For example, the command name "do_something" maps to the method name
"_executeDoSomethingCommand".

Keyboard input interpreter commands are executed somewhat differently
from commands of other commandables. To execute a command of a
non-interpreter commandable, the interpreter binds the command arguments
as temporary variables in the interpreter's command execution environment,
invokes the appropriate method on the commandable with the environment,
and then clears all temporary variables from the environment. To execute
an interpreter command, the interpreter simply calls the appropriate
method, without any binding and clearing of temporary variables: any
needed environment manipulation is left to the command.

TODO: Add discussion of special keys to the above.
TODO: Add discussion of commandable interface.
TODO: Add discussion of commandable delegates, including sharing.

Keyboard input interpreter data:

    input buffer
    environment
    commandable stack
        Each commandable (clip album, clip view, overlay)
        has a name that can be used to look up its key bindings.
        Contents of commandable stack track components under mouse.
    key bindings
        {commandable name: key bindings} map


Terms:

keyboard input interpreter
commandable (class with particular interface)
commandable delegate

key bindings
key binding (binds key sequence to command)
key sequence
command
command name
command parameter
command parameter name
command parameter value

command execution environment (or simply environment)
persistent variables
temporary variables


Presets:

Clip Album Settings
Clip Album Key Bindings


*/


/*

TODO: Add support for optional command arguments with default values.
Then, for example, the clip album `play_selected_clip` command could
have an optional `playback_rate` argument, obviating the existing
`play_selected_clip_at_rate` command.

We can do this by augmenting the kinds of JSON that describe commands.

For example, one might write:

    {
        'name': 'play_selected_clip',
        'args': [
            {
                'name': 'playback_rate',
                'default': 1
            }
        ]
    }
    
to describe a command with an optional argument.

Using JSON objects to describe commands and command arguments could also
allow us to specify things like documentation and argument types.

For commands without arguments, we might allow specification of the
command with  just the name of the command as a string instead of
putting the string in a list, e.g.:

    'show_next_page'
    
rather than:

    ['show_next_page']
    
This will become less useful the more completely we specify commands,
e.g. by including documentation, since then fewer commands will be
specifiable by just their names.

*/


// I don't think we want this to be a JavaScript class, but it might
// make sense for it to be a TypeScript interface.
/*
export class Commandable {

    get commandableName() { }

    hasCommand(commandName) { }

    executeCommand(command, env) { }

}
*/


const _SPECIAL_KEY_BINDINGS_NAME = 'Special';

const _DEFAULT_SPECIAL_KEY_BINDINGS = {
    '\\': ['clear_key_buffer_and_temporary_variables']
};


export class KeyboardInputInterpreter {


    static get KEY_SEQUENCE_UNRECOGNIZED() { return 0; }
    static get KEY_SEQUENCE_PARTIAL() { return 1; }
    static get KEY_SEQUENCE_COMPLETE() { return 2; }


	constructor(settings) {

        settings = this._updateSettingsIfNeeded(settings);

        // `this._specialKeyBindings` is a map from single keys to
        // commands.
        //
        // `this._regularKeyBindings` is a map from commandable names
        // to maps from key sequences to commands.
        [this._specialKeyBindings, this._regularKeyBindings] =
            this._createKeyBindingMaps(settings);

        // `this._keySequencePrefixes` is a map from commandable names
        // to sets of proper prefixes of key binding key sequences.
        this._keySequencePrefixes = this._createKeySequencePrefixesMap();

		this._environment = new Environment();
        this._commandable = new _InterpreterCommandable(this);
        this._commandables = new _InterpreterCommandables(this._commandable);

        this._executeInitializationCommands(settings);

        this._clearKeyBuffer();

	}


    // Udates settings from old format to new format if needed.
    _updateSettingsIfNeeded(settings) {

        const globals = settings.globals;
        if (globals !== undefined) {
            const names = Object.getOwnPropertyNames(globals);
            settings.interpreterInitializationCommands =
                names.map(n => ['set_persistent_variable', n, globals[n]]);
            delete settings.globals;
        }

        const commands = settings.commands;
        if (commands !== undefined) {
            settings.keyBindings = { 'Clip Album': commands };
            delete settings.commands;
        }

        return settings;

    }


    _createKeyBindingMaps(settings) {

        const keyBindings = settings.keyBindings;

        if (keyBindings === undefined)
            throw Error(
                'Keyboard input interpreter settings lack key bindings.');

        // TODO: Validate key bindings. Bindings should be an object
        // whose properties map string commandable names to objects
        // whose properties map string key sequences to commands.
        // A command is an array with at least one element, whose
        // first element is a string. Special binding key sequences
        // should be of length one.

        const specialKeyBindings =
            this._createSpecialKeyBindingsMap(keyBindings);

        const regularKeyBindings =
            this._createRegularKeyBindingsMap(keyBindings);

        return [specialKeyBindings, regularKeyBindings];

    }


    _createSpecialKeyBindingsMap(keyBindings) {

        const bindings = keyBindings[_SPECIAL_KEY_BINDINGS_NAME];

        if (bindings === undefined)
            return this._createKeyBindingsMap(_DEFAULT_SPECIAL_KEY_BINDINGS);
        else
            return this._createKeyBindingsMap(bindings);

    }


    _createKeyBindingsMap(bindings) {
        const keySequences = Object.getOwnPropertyNames(bindings);
        const entries = keySequences.map(k => [k, bindings[k]]);
        return new Map(entries);
    }


    _createRegularKeyBindingsMap(bindings) {

        const commandableNames = Object.getOwnPropertyNames(bindings).filter(
            n => n !== _SPECIAL_KEY_BINDINGS_NAME
        );

        const entries = commandableNames.map(
            n => [n, this._createKeyBindingsMap(bindings[n])]
        );

        return new Map(entries);

    }


    _createKeySequencePrefixesMap() {

        const bindingEntries = Array.from(this._regularKeyBindings.entries())

        const prefixEntries = bindingEntries.map(
            ([name, bindings]) =>
                [name, this._createKeySequencePrefixesSet(bindings)]
        );

        return new Map(prefixEntries);

    }


    // Gets the set of all proper prefixes of the key sequences of
    // the specified key bindings.
    _createKeySequencePrefixesSet(keyBindings) {

        const prefixes = new Set();

        for (const keySequence of keyBindings.keys())
            for (let i = 1; i < keySequence.length; i++)
                prefixes.add(keySequence.slice(0, i));

        return prefixes;

    }


    pushCommandable(commandable) {
        // console.log(`pushCommandable "${commandable.commandableName}"`);
        this._commandables.push(commandable);
    }


    popCommandable() {
        const commandable = this._commandables.pop();
        // console.log(`popCommandable "${commandable.commandableName}"`);
        return commandable;
    }


    _executeInitializationCommands(settings) {

        const commands = settings.interpreterInitializationCommands;

        if (commands !== undefined)
            for (const command of commands)
                this._commandable.executeCommand(command, this._environment);

    }


    _clearKeyBuffer() {
		this._keyBuffer = '';
	}


    handleKey(key) {

		// console.log(
        //     'KeyboardInputInterpreter.handleKey', key, this._keyBuffer);

        const command = this._specialKeyBindings.get(key);

        if (command !== undefined) {
            // key is a special key

            this._commandable.executeCommand(command, this._environment);
            return [KeyboardInputInterpreter.KEY_SEQUENCE_COMPLETE, key];

        } else {
            // key is not a special key

    		const keys = this._keyBuffer + key;

            // Note that commandables are iterated from top to bottom of stack.
            for (const commandable of this._commandables) {

                const commandableName = commandable.commandableName;
                const keyBindings =
                    this._regularKeyBindings.get(commandableName);

                if (keyBindings === undefined)
                    // no key bindings for this commandable

                    continue;

                const command = keyBindings.get(keys);

                if (command !== undefined) {
                    // `keys` is bound for this commandable

                    this._executeCommand(commandable, command);
                    return [
                        KeyboardInputInterpreter.KEY_SEQUENCE_COMPLETE, keys];

                } else {

                    const prefixes =
                        this._keySequencePrefixes.get(commandableName);

                    if (prefixes.has(keys)) {
                        // `keys` is proper prefix of key sequence bound for
                        // this commandable

                        this._keyBuffer = keys;
                        return [
                            KeyboardInputInterpreter.KEY_SEQUENCE_PARTIAL,
                            keys
                        ];

                    }

                }

            }

            // If we get here, `keys` is not a prefix of any key sequence
            // bound for any commandable.
            this._clearKeyBuffer();
            this._environment.clearTemporaryVariables();
            return [KeyboardInputInterpreter.KEY_SEQUENCE_UNRECOGNIZED, keys];

        }

	}


    _executeCommand(commandable, command) {

        const commandName = command[0];

        if (commandable.hasCommand(commandName)) {

            this._executeCommandAux(commandable, command);

        } else if (this._commandable.hasCommand(commandName)) {

            this._executeCommandAux(this._commandable, command);

        } else {

            throw new Error(
                `Unrecognized command "${commandName}" for ` +
                `"${commandable.name}".`);

        }

    }


    _executeCommandAux(commandable, command) {

        try {

            commandable.executeCommand(command, this._environment);

        } finally {

            // Always clear key buffer, regardless of whether or not
            // command execution succeeds.
            this._clearKeyBuffer();

        }

    }


}


export class Environment {


	constructor() {
		this._persistent_variables = new Map();
		this._temporary_variables = new Map();
	}


    setPersistentVariable(name, value) {
    	this._persistent_variables.set(name, value);
    }


    deletePersistentVariable(name) {
    	delete this._persistent_variables.delete(name);
    }


    clearPersistentVariables() {
    	this._persistent_variables.clear();
    }


    setTemporaryVariable(name, value) {
    	this._temporary_variables.set(name, value);
    }


    deleteTemporaryVariable(name) {
    	delete this._temporary_variables.delete(name);
    }


    clearTemporaryVariables() {
    	this._temporary_variables.clear();
    }


    get(name) {

        let value = this._temporary_variables.get(name);
    	if (value !== undefined)
    		return value;

    	value = this._persistent_variables.get(name);
        if (value !== undefined)
    		return value;

        return undefined;

    }


    getRequired(name) {

    	const value = this.get(name);

    	if (value === undefined)
    		throw new Error(
    			`Required keyboard input interpreter variable "${name}" ` +
                `not found.`);

    	else
    	    return value;

    }


}


export class CommandableDelegate {


    constructor(commandSpecs) {
        this._commandSpecs = commandSpecs;
        this._commandNames = new Set(commandSpecs.map(s => s[0]));
        this._paramNames = _createParamNamesMap(commandSpecs);
    }


    get commandSpecs() {
        return this._commandSpecs;
    }


    hasCommand(commandName) {
        return this._commandNames.has(commandName);
    }


    executeCommand(command, commandable, env) {

        // We assume that `command` is a list of strings with length
        // greater than zero.
        const [commandName, ...paramValues] = command;

        this._checkCommandName(commandName, commandable);

        const paramNames = this._paramNames.get(commandName);

        this._checkParamValues(
            paramValues, paramNames.length, commandName, commandable);

        this._executeCommand(
            commandName, paramNames, paramValues, commandable, env);

    }


    _checkCommandName(commandName, commandable) {

        if (!this._paramNames.has(commandName))
            throw new Error(
                `"${commandable.commandableName}" has no command ` +
                `"${commandName}".`);

    }


    _checkParamValues(values, numParams, commandName, commandable) {

		if (values.length !== numParams) {

            const commandableName = commandable.commandableName;
			const suffix = numParams === 1 ? '' : 's';

			throw new Error(
				`Command "${commandName}" of "${commandableName}" ` +
                `requires ${numParams} parameter value${suffix} but ` +
                `received ${values.length}.`);

		}

	}


    _executeCommand(commandName, paramNames, paramValues, commandable, env) {

        const methodName = this._getCommandMethodName(commandName);
        this._checkCommandMethod(commandable, methodName);

        // Add command parameters to temporary variables.
		for (const [i, name] of paramNames.entries())
			env.setTemporaryVariable(name, paramValues[i]);

		try {

            // For some reason, the following does not work:
            //
            //     method = commandable[methodName];
            //     method(env);
            //
            // but this does:
            //
            //     commandable[methodName](env);
            //
            // I haven't yet taken the time to understand why, but it
            // appears to have something to do with how JavaScript's
            // `this` works.

            commandable[methodName](env);


		} finally {

		    // Clear temporary variables. Note that this includes *all*
            // temporary variables, such as any that may have been set
            // with the keyboard input interpreter's
            // `set_temporary_variable` command, not just those for the
            // parameters of this command.
		    env.clearTemporaryVariables();

		}

    }


    _getCommandMethodName(commandName) {
        const parts = commandName.split('_');
        const capitalizedParts = parts.map(this._capitalize);
        return '_execute' + capitalizedParts.join('') + 'Command';
    }


    _capitalize(s) {
        if (s.length === 0)
            return s;
        else
            return s[0].toUpperCase() + s.slice(1);
    }


    _checkCommandMethod(commandable, methodName) {

        if (commandable[methodName] === undefined)
            throw new Error(
                `Could not find method "${methodName}" for ` +
                `"${commandable.commandableName}".`);

    }


}


function _createParamNamesMap(commandSpecs) {
    const pairs = commandSpecs.map(s => [s[0], s.slice(1)]);
    return new Map(pairs);
}


const _INTERPRETER_COMMAND_SPECS = [


    ['set_persistent_variable', 'name', 'value'],
    ['delete_persistent_variable', 'name'],
    ['clear_persistent_variables'],

    ['set_temporary_variable', 'name', 'value'],
    ['delete_temporary_variable', 'name'],
    ['clear_temporary_variables'],

    ['clear_key_buffer'],
    ['clear_key_buffer_and_temporary_variables'],


    // Old versions of above commands. We will remove these at some
    // point but retain them for now.

    ['set_global', 'name', 'value'],
    ['delete_global', 'name'],
    ['clear_globals'],

    ['set_local', 'name', 'value'],
    ['delete_local', 'name'],
    ['clear_locals'],

    ['clear_command'],
    ['clear_command_and_locals']


];


class _InterpreterCommandableDelegate extends CommandableDelegate {


    constructor() {
        super(_INTERPRETER_COMMAND_SPECS);
    }


    // By default, a `CommandableDelegate` creates temporary variables
    // in the command execution environment before invoking the appropriate
    // command method of its commandable, and then clears all of the
    // temporary variables of the environment after the method invocation
    // completes. An `_InterpreterCommandableDelegate`, in contrast,
    // does not manipulate the environment at all by default: all
    // such manipulations are left to the command methods.
    _executeCommand(commandName, paramNames, paramValues, commandable, env) {
        const methodName = this._getCommandMethodName(commandName);
        this._checkCommandMethod(commandable, methodName);
        commandable[methodName](env, ...paramValues);
    }


}


const _interpreterCommandableDelegate =
    new _InterpreterCommandableDelegate();


class _InterpreterCommandable {


    constructor(interpreter) {
        this._interpreter = interpreter;
        this._commandableDelegate = _interpreterCommandableDelegate;
    }


    get commandableName() {
        return 'Keyboard Input Interpreter';
    }


    hasCommand(commandName) {
        return this._commandableDelegate.hasCommand(commandName);
    }


    executeCommand(command, env) {
        this._commandableDelegate.executeCommand(command, this, env);
    }


    _executeSetPersistentVariableCommand(env, name, value) {
		env.setPersistentVariable(name, value);
	}


    _executeDeletePersistentVariableCommand(env, name) {
        env.deletePersistentVariable(name);
    }


    _executeClearPersistentVariablesCommand(env) {
        env.clearPersistentVariables();
    }


    _executeSetTemporaryVariableCommand(env, name, value) {
        env.setTemporaryVariable(name, value);
    }


    _executeDeleteTemporaryVariableCommand(env, name) {
        env.deleteTemporaryVariable(name);
    }


    _executeClearTemporaryVariablesCommand(env) {
        env.clearTemporaryVariables();
    }


    _executeClearKeyBufferCommand(env) {
        this._interpreter._clearKeyBuffer();
    }


    _executeClearKeyBufferAndTemporaryVariablesCommand(env) {
        this._interpreter._clearKeyBuffer();
        env.clearTemporaryVariables();
    }


    _executeSetGlobalCommand(env, name, value) {
        env.setPersistentVariable(name, value);
    }


    _executeDeleteGlobalCommand(env, name) {
        env.deletePersistentVariable(name);
    }


    _executeClearGlobalsCommand(env) {
        env.clearPersistentVariables();
    }


    _executeSetLocalCommand(env, name, value) {
        env.setTemporaryVariable(name, value);
    }


    _executeDeleteLocalCommand(env, name) {
        env.deleteTemporaryVariable(name);
    }


    _executeClearLocalsCommand(env) {
        env.clearTemporaryVariables();
    }


    _executeClearCommandCommand(env) {
        this._interpreter._clearKeyBuffer();
    }


    _executeClearCommandAndLocalsCommand(env) {
        this._interpreter._clearKeyBuffer();
        env.clearTemporaryVariables();
    }


}


// Stack of commandables for a keyboard input interpreter.
//
// The stack is initialized with an interpreter commandable that cannot
// be popped.
//
// The stack is iterable. Its elements are iterated from top to bottom.
class _InterpreterCommandables {


    constructor(interpreterCommandable) {
        this._commandables = [interpreterCommandable];
    }


    push(commandable) {
        this._commandables.push(commandable);
    }


    pop() {
        if (this._commandables.length == 1)
            return undefined;
        else
            return this._commandables.pop();
    }


    *[Symbol.iterator]() {
        for (let i = this._commandables.length - 1; i >= 0; i--)
            yield this._commandables[i];
    }


}
