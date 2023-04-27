from typing import Literal, get_args, get_origin, Any

def is_assignable(from_type: Any, to_type: Any) -> bool:
    # Handle parameterized generic types like List and Tuple
    if get_origin(to_type) in (list, tuple):
        if get_origin(from_type) != get_origin(to_type):
            return False
        from_args = get_args(from_type)
        to_args = get_args(to_type)
        if len(from_args) != len(to_args):
            return False
        return all(is_assignable(from_arg, to_arg) for from_arg, to_arg in zip(from_args, to_args))
    
    # Handle special case when from_type is a Literal type
    if get_origin(from_type) == Literal:
        # Check if all possible values of the Literal type are assignable to to_type
        return all(isinstance(value_type, to_type) for value_type in get_args(from_type))

    # Check if from_type is a subclass of to_type
    return issubclass(from_type, to_type)

is_assignable(tuple[int, int], tuple[int, ...])
