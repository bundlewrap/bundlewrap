from multiprocessing import Pool


def __parallel_method_helper((obj_name, obj, methodname, args, kwargs)):
    return {
        obj_name: getattr(obj, methodname)(*args, **kwargs),
    }


def parallel_method(obj_dict, methodname, args, kwargs, workers=64):
    """
    This will call a method on a bunch of similar objects in parallel.

        obj_dict:    a dictionary mapping any kind of identifier
                     to the target objects
        methodname:  name of the method that is called on objects in
                     obj_dict
        args:        list of positional arguments passed to method
        kwargs:      dictionary of keyword arguments passed to method
        workers:     amount of worker processes

    Returns a dictionary mapping the identifiers from obj_dict to
    return values of the method calls.
    """
    runlist = []
    for obj_name, obj in obj_dict.iteritems():
        runlist.append((obj_name, obj, methodname, args, kwargs))

    results = {}
    p = Pool(workers)
    for result in p.map(__parallel_method_helper, runlist):
        results.update(result)
    return results
