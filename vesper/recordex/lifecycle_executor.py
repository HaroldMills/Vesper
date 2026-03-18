import sys


class LifecycleExecutor:

    """
    Class for executing an object's lifecycle with exception handling
    and cleanup.

    A *lifecycle* is a sequence of *phases* that can be executed for a
    Python object. Each phase is represented by a *method*, a *logger*,
    and a *cleanup method*. The method is a zero-argument method of the
    object that executes the phase. The logger is either a Python
    `logging` module or `None`. The cleanup method is either the method
    of a later lifecycle phase, called the *cleanup phase* of the phase,
    or `None`.
    
    A *lifecycle executor* executes the phases of a lifecycle in order.
    If the method of a phase raises an exception, the executor logs
    an error message to the phase's logger if there is one or to standard
    error if not. After logging the error message, the executor either
    advances to the failed phase's cleanup phase if there is one or
    aborts lifecycle execution if not.
    """


    def __init__(self, obj, object_name, lifecycle):

        """
        Initialize this lifecycle executor.

        Parameters
        ----------
        obj : obj
            The object whose lifecycle is to be executed.
        object_name : str
            The name of the object, for error messages.
        lifecycle : sequence
            A sequence of tuples, where each tuple specifies a lifecycle
            phase. Each tuple has the form
            `(method_name, logger, cleanup_method_name)`. In such a tuple,
            the `method_name` item is the name of the zero-argument `object`
            method that implements the lifecycle phase. The `logger` item
            is either a Python `logging` module logger to log an error
            message to if the method raises an exception or `None` if the
            error message should be logged to standard error. The
            `cleanup_method_name` item is either the method name of a
            later phase that the executor should advance to if the method
            of the current phase raises an exception or `None` if
            lifecycle execution should be aborted.
        """

        self._object = obj
        self._object_name = object_name
        self._lifecycle = self._compile_lifecycle(lifecycle)


    def _compile_lifecycle(self, lifecycle):

        """
        Compile a lifecycle specification.

        Parameters
        ----------
        lifecycle : sequence
            See the `lifecycle` parameter of the initializer.

        Returns
        -------
        sequence
            A sequence of tuples, each of which specifies a lifecycle phase.
            Each tuple is of the form `(method, logger, cleanup_phase_num)`.
            Such a tuple is much like a tuple of the `lifecycle` parameter
            except that `method` is the lifecycle method rather than its
            name and `cleanup_phase_num` is the index of the cleanup phase
            rather than its method name.
        """

        phase_nums = {
            getattr(self._object, method_name): i
            for i, (method_name, _, _) in enumerate(lifecycle)
        }

        def compile(method_name, logger, cleanup_method_name):

            method = getattr(self._object, method_name)

            if cleanup_method_name is None:
                cleanup_phase_num = None
            else:
                cleanup_method = getattr(self._object, cleanup_method_name)
                cleanup_phase_num = phase_nums[cleanup_method]

            return method, logger, cleanup_phase_num
        
        return tuple([compile(*d) for d in lifecycle])


    def execute_lifecycle(self):

        phase_count = len(self._lifecycle)
        phase_num = 0

        while phase_num != phase_count:

            # Get lifecycle phase data.
            method, logger, cleanup_phase_num = self._lifecycle[phase_num]

            # Execute phase method.
            try:
                method()

            except Exception as e:
                # phase method raised an exception

                self._log_method_execution_error(
                    method, e, logger, cleanup_phase_num)
                
                if cleanup_phase_num is None:
                    # no cleanup phase specified

                    break

                else:
                    # cleanup phase specified

                    # Continue lifecycle execution at cleanup phase.
                    phase_num = cleanup_phase_num

            else:
                # method executed successfully

                # Move on to next lifecycle method.
                phase_num += 1


    def _log_method_execution_error(
            self, method, exception, logger, cleanup_phase_num):
        
        if cleanup_phase_num is None:
            # no cleanup method specified

            cleanup_text = 'Lifecycle execution will be aborted.'

        else:
            # cleanup method specified

            cleanup_method = self._lifecycle[cleanup_phase_num][0]
            cleanup_text = (
                f'Lifecycle execution will continue at cleanup method '
                f'"{cleanup_method.__name__}".')

        message = (
            f'Attempt to execute {self._object_name} lifecycle method '
            f'"{method.__name__}" unexpectedly raised '
            f'"{type(exception).__name__}" exception. {cleanup_text} '
            f'Exception message was: {exception}')
        
        if logger is None:
            print(message, file=sys.stderr)
        else:
            logger.error(message)
