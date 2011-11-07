from islpy._isl import *
from islpy.version import *


_CHECK_DIM_TYPES = [
        dim_type.in_, dim_type.param, dim_type.set]

_DEFAULT_CONTEXT = Context()

def _add_functionality():
    import islpy._isl as _isl

    ALL_CLASSES = [getattr(_isl, cls) for cls in dir(_isl) if cls[0].isupper()]

    # {{{ generic initialization

    def obj_new_from_string(cls, s, context=None):
        """Construct a new object from :class:`str` s.

        :arg context: a :class:`islpy.Context` to use. If not supplied, use a
            global default context.
        """

        if context is None:
            context = _DEFAULT_CONTEXT

        result = cls.read_from_str(context, s)
        result._made_from_string = True
        return result

    def obj_bogus_init(self, s, context=None):
        assert self._made_from_string
        del self._made_from_string

    for cls in ALL_CLASSES:
        if hasattr(cls, "read_from_str"):
            cls.__new__ = staticmethod(obj_new_from_string)
            cls.__init__ = obj_bogus_init

    # }}}

    # {{{ printing

    def generic_str(self):
        prn = Printer.to_str(self.get_ctx())
        getattr(prn, "print_"+self._base_name)(self)
        return prn.get_str()

    def generic_repr(self):
        prn = Printer.to_str(self.get_ctx())
        getattr(prn, "print_"+self._base_name)(self)
        return "%s(\"%s\")" % (
                type(self).__name__, prn.get_str())

    for cls in ALL_CLASSES:
        if hasattr(Printer, "print_"+cls._base_name):
            cls.__str__ = generic_str
            cls.__repr__ = generic_repr

    # }}}

    # {{{ rich comparisons

    def obj_eq(self, other):
        return self.is_equal(other)

    def obj_ne(self, other):
        return not self.is_equal(other)

    for cls in ALL_CLASSES:
        if hasattr(cls, "is_equal"):
            cls.__eq__ = obj_eq
            cls.__ne__ = obj_ne

    def obj_lt(self, other): return self.is_strict_subset(other)
    def obj_le(self, other): return self.is_subset(other)
    def obj_gt(self, other): return other.is_strict_subset(self)
    def obj_ge(self, other): return other.is_subset(self)

    for cls in [BasicSet, BasicMap, Set, Map]:
        cls.__lt__ = obj_lt
        cls.__le__ = obj_le
        cls.__gt__ = obj_gt
        cls.__ge__ = obj_ge

    # }}}

    # {{{ Python set-like behavior

    def obj_or(self, other):
        try:
            return self.union(other)
        except TypeError:
            return NotImplemented

    def obj_and(self, other):
        try:
            return self.intersect(other)
        except TypeError:
            return NotImplemented

    def obj_sub(self, other):
        try:
            return self.subtract(other)
        except TypeError:
            return NotImplemented

    for cls in [BasicSet, BasicMap, Set, Map]:
        cls.__or__ = obj_or
        cls.__and__ = obj_and
        cls.__sub__ = obj_sub

    #}}}

    # {{{ Space

    def space_get_var_dict(self, dimtype=None):
        """Return a dictionary mapping variable names to tuples of (:class:`dim_type`, index).

        :param dimtype: None to get all variables, otherwise
            one of :class:`dim_type`.
        """
        result = {}

        def set_dim_name(name, tp, idx):
            if name in result:
                raise RuntimeError("non-unique var name '%s' encountered" % name)
            result[name] = tp, idx

        if dimtype is None:
            types = _CHECK_DIM_TYPES
        else:
            types = [dimtype]

        for tp in types:
            for i in range(self.dim(tp)):
                name = self.get_dim_name(tp, i)
                if name is not None:
                    set_dim_name(name, tp, i)

        return result

    def space_create_from_names(ctx, set=None, in_=None, out=None, params=[]):
        """Create a :class:`Space` from lists of variable names.

        :param set_`: names of `set`-type variables.
        :param in_`: names of `in`-type variables.
        :param out`: names of `out`-type variables.
        :param params`: names of parameter-type variables.
        """
        dt = dim_type

        if set is not None:
            if in_ is not None or out is not None:
                raise RuntimeError("must pass only one of set / (in_,out)")

            result = Space.set_alloc(ctx, nparam=len(params),
                    dim=len(set))

            for i, name in enumerate(set):
                result = result.set_dim_name(dt.set, i, name)

        elif in_ is not None and out is not None:
            if set is not None:
                raise RuntimeError("must pass only one of set / (in_,out)")

            result = Space.alloc(ctx, nparam=len(params),
                    n_in=len(in_), n_out=len(out))

            for i, name in enumerate(in_):
                result = result.set_dim_name(dt.in_, i, name)

            for i, name in enumerate(out):
                result = result.set_dim_name(dt.out, i, name)
        else:
            raise RuntimeError("invalid parameter combination")

        for i, name in enumerate(params):
            result = result.set_dim_name(dt.param, i, name)

        return result

    Space.create_from_names = staticmethod(space_create_from_names)
    Space.get_var_dict = space_get_var_dict

    # }}}

    # {{{ coefficient wrangling

    def obj_set_coefficients(self, dim_tp, args):
        """
        :param dim_tp: :class:`dim_type`
        :param args: :class:`list` of coefficients, for indices `0..len(args)-1`.

        .. versionchanged:: 2011.3
            New for :class:`Aff`
        """
        for i, coeff in enumerate(args):
            self = self.set_coefficient(dim_tp, i, coeff)

        return self

    def obj_set_coefficients_by_name(self, iterable, name_to_dim=None):
        """Set the coefficients and the constant.

        :param iterable: a :class:`dict` or iterable of :class:`tuple`
            instances mapping variable names to their coefficients.
            The constant is set to the value of the key '1'.

        .. versionchanged:: 2011.3
            New for :class:`Aff`
        """
        try:
            iterable = iterable.iteritems()
        except AttributeError:
            pass

        if name_to_dim is None:
            name_to_dim = self.get_space().get_var_dict()

        for name, coeff in iterable:
            if name == 1:
                self = self.set_constant(coeff)
            else:
                tp, idx = name_to_dim[name]
                self = self.set_coefficient(tp, idx, coeff)

        return self

    def obj_get_coefficients_by_name(self, dimtype=None, dim_to_name=None):
        """Return a dictionary mapping variable names to coefficients.

        :param dimtype: None to get all variables, otherwise
            one of :class:`dim_type`.

        .. versionchanged:: 2011.3
            New for :class:`Aff`
        """
        if dimtype is None:
            types = _CHECK_DIM_TYPES
        else:
            types = [dimtype]

        result = {}
        for tp in types:
            for i in range(self.get_space().dim(tp)):
                coeff = self.get_coefficient(tp, i)
                if coeff:
                    if dim_to_name is None:
                        name = self.get_dim_name(tp, i)
                    else:
                        name = dim_to_name[(tp, i)]

                    result[name] = coeff

        const = self.get_constant()
        if const:
            result[1] = const

        return result

    for coeff_class in [Constraint, Aff]:
        coeff_class.set_coefficients = obj_set_coefficients
        coeff_class.set_coefficients_by_name = obj_set_coefficients_by_name
        coeff_class.get_coefficients_by_name = obj_get_coefficients_by_name

    # }}}

    # {{{ Constraint

    def eq_from_names(space, coefficients={}):
        """Create a constraint `const + coeff_1*var_1 +... == 0`.

        :param space: :class:`Space`
        :param coefficients: a :class:`dict` or iterable of :class:`tuple`
            instances mapping variable names to their coefficients
            The constant is set to the value of the key '1'.

        .. versionchanged:: 2011.3
            Eliminated the separate *const* parameter.
        """
        c = Constraint.equality_alloc(space)
        return c.set_coefficients_by_name(coefficients)

    def ineq_from_names(space, coefficients={}):
        """Create a constraint `const + coeff_1*var_1 +... >= 0`.

        :param space: :class:`Space`
        :param coefficients: a :class:`dict` or iterable of :class:`tuple` 
            instances mapping variable names to their coefficients
            The constant is set to the value of the key '1'.

        .. versionchanged:: 2011.3
            Eliminated the separate *const* parameter.
        """
        c = Constraint.inequality_alloc(space)
        return c.set_coefficients_by_name(coefficients)

    Constraint.eq_from_names = staticmethod(eq_from_names)
    Constraint.ineq_from_names = staticmethod(ineq_from_names)

    # }}}

    def basic_obj_get_constraints(self):
        """Get a list of constraints."""
        result = []
        self.foreach_constraint(result.append)
        return result

    # {{{ BasicSet

    BasicSet.get_constraints = basic_obj_get_constraints

    # }}}

    # {{{ BasicMap

    BasicMap.get_constraints = basic_obj_get_constraints

    # }}}

    # {{{ Set

    def set_get_basic_sets(self):
        """Get the list of :class:`BasicSet` instances in this :class:`Set`."""
        result = []
        self.foreach_basic_set(result.append)
        return result

    Set.get_basic_sets = set_get_basic_sets

    # }}}

    # {{{ Map

    def map_get_basic_maps(self):
        """Get the list of :class:`BasicMap` instances in this :class:`Map`."""
        result = []
        self.foreach_basic_map(result.append)
        return result

    Map.get_basic_maps = map_get_basic_maps

    # }}}

    # {{{ PwAff

    def pwaff_get_pieces(self):
        """
        :return: list of (:class:`Set`, :class:`Aff`)
        """

        result = []
        def append_tuple(*args):
            result.append(args)

        self.foreach_piece(append_tuple)
        return result

    def pwaff_get_aggregate_domain(self):
        """
        :return: a :class:`Set` that is the union of the domains of all pieces
        """

        result = Set.empty(self.get_domain_space())
        for dom, _ in self.get_pieces():
            result = result.union(dom)

        return result

    PwAff.get_aggregate_domain = pwaff_get_aggregate_domain
    PwAff.get_pieces = pwaff_get_pieces

    # }}}

    # {{{ aff arithmetic

    def _number_to_aff(template, num):
        number_aff = Aff.zero_on_domain(template.get_domain_space())
        number_aff = number_aff.set_constant(num)

        if isinstance(template, PwAff):
            result = PwAff.empty(template.get_space())
            for set, _ in template.get_pieces():
                result = result.cond(set, number_aff, result)
            return result

        else:
            return number_aff

    def aff_add(self, other):
        if not isinstance(other, (Aff, PwAff)):
            other = _number_to_aff(self, other)

        try:
            return self.add(other)
        except TypeError:
            return NotImplemented

    def aff_sub(self, other):
        if not isinstance(other, (Aff, PwAff)):
            other = _number_to_aff(self, other)

        try:
            return self.sub(other)
        except TypeError:
            return NotImplemented

    def aff_rsub(self, other):
        if not isinstance(other, (Aff, PwAff)):
            other = _number_to_aff(self, other)

        return -self + other

    def aff_mul(self, other):
        if not isinstance(other, (Aff, PwAff)):
            other = _number_to_aff(self, other)

        try:
            return self.mul(other)
        except TypeError:
            return NotImplemented

    for aff_class in [Aff, PwAff]:
        aff_class.__add__ = aff_add
        aff_class.__radd__ = aff_add
        aff_class.__sub__ = aff_sub
        aff_class.__rsub__ = aff_rsub
        aff_class.__mul__ = aff_mul
        aff_class.__rmul__ = aff_mul
        aff_class.__neg__ = aff_class.neg
        aff_class.__mod__ = aff_class.mod

    # }}}

    # {{{ add automatic 'self' upcasts

    # note: automatic upcasts for method arguments are provided through
    # 'implicitly_convertible' on the C++ side of the wrapper.

    class UpcastWrapper(object):
        def __init__(self, method, upcast):
            self.method = method
            self.upcast = upcast

    def add_upcasts(basic_class, special_class, upcast_method):
        from functools import update_wrapper

        from inspect import ismethod
        for method_name in dir(special_class):
            if hasattr(basic_class, method_name):
                continue

            method = getattr(special_class, method_name)

            if ismethod(method):
                def make_wrapper(method, upcast):
                    # This function provides a scope in which method and upcast
                    # are not changed from one iteration of the enclosing for
                    # loop to the next.

                    def wrapper(basic_instance, *args, **kwargs):
                        special_instance = upcast(basic_instance)
                        return method(special_instance, *args, **kwargs)

                    return wrapper

                wrapper = make_wrapper(method, upcast_method)
                setattr(basic_class, method_name, update_wrapper(wrapper, method))

    for args_triple in [
            (BasicSet, Set, Set.from_basic_set),
            (BasicMap, Map, Map.from_basic_map),
            (Set, UnionSet, UnionSet.from_set),
            (Map, UnionMap, UnionMap.from_map),

            (BasicSet, UnionSet, lambda x: UnionSet.from_set(Set.from_basic_set(x))),
            (BasicMap, UnionMap, lambda x: UnionMap.from_map(Map.from_basic_map(x))),

            (Aff, PwAff, PwAff.from_aff),
            (Space, LocalSpace, LocalSpace.from_space),
            ]:
        add_upcasts(*args_triple)

    # }}}

    # {{{ project_out_except

    def obj_project_out_except(obj, names, types):
        """
        :param types: list of :class:`dim_type` determining
            the types of axes to project out
        :param names: names of axes matching the above which
            should be left alone by the projection

        .. versionadded:: 2011.3
        """

        for tp in types:
            while True:
                space = obj.get_space()
                var_dict = space.get_var_dict(tp)

                all_indices = set(xrange(space.dim(tp)))
                leftover_indices = set(var_dict[name][1] for name in names
                        if name in var_dict)
                project_indices = all_indices-leftover_indices
                if not project_indices:
                    break

                min_index = min(project_indices)
                count = 1
                while min_index+count in project_indices:
                    count += 1

                obj = obj.project_out(tp, min_index, count)

        return obj

    # }}}

    # {{{ eliminate_except

    def obj_eliminate_except(obj, names, types):
        """
        :param types: list of :class:`dim_type` determining
            the types of axes to eliminate
        :param names: names of axes matching the above which
            should be left alone by the eliminate

        .. versionadded:: 2011.3
        """

        already_eliminated = set()

        for tp in types:
            space = obj.get_space()
            var_dict = space.get_var_dict(tp)
            to_eliminate = (
                    set(xrange(space.dim(tp)))
                    - set(var_dict[name][1] for name in names
                        if name in var_dict))

            while to_eliminate:
                min_index = min(to_eliminate)
                count = 1
                while min_index+count in to_eliminate:
                    count += 1

                obj = obj.eliminate(tp, min_index, count)

                to_eliminate -= set(xrange(min_index, min_index+count))

        return obj

    # }}}

    # {{{ add_constraints

    def obj_add_constraints(obj, constraints):
        """
        .. versionadded:: 2011.3
        """

        for cns in constraints:
            obj = obj.add_constraint(cns)

        return obj

    # }}}

    for c in [BasicSet, BasicMap, Set, Map]:
        c.project_out_except = obj_project_out_except
        c.eliminate_except = obj_eliminate_except
        c.add_constraints = obj_add_constraints




_add_functionality()




def align_spaces(obj, tgt, obj_bigger_ok=False):
    """
    Try to make the space in which *obj* lives the same as that of *tgt* by
    adding/matching named dimensions.

    :param obj_bigger_ok: If *True*, no error is raised if the resulting *obj*
        has more dimensions than *tgt*.
    """
    for dt in _CHECK_DIM_TYPES:
        obj_names = [obj.get_dim_name(dt, i) for i in xrange(obj.dim(dt))]
        tgt_names = [tgt.get_dim_name(dt, i) for i in xrange(tgt.dim(dt))]

        if None in tgt_names:
            all_nones = [None] * len(tgt_names)
            if tgt_names == all_nones and obj_names == all_nones:
                # that's ok
                continue

            raise RuntimeError("tgt may not contain any unnamed dimensions")

        obj_names = set(obj_names) - set([None])
        tgt_names = set(tgt_names) - set([None])

        names_in_both = obj_names & tgt_names

        i = 0
        while i < tgt.dim(dt):
            tgt_name = tgt.get_dim_name(dt, i)

            if tgt_name in names_in_both:
                assert i < obj.dim(dt)

                obj_name = obj.get_dim_name(dt, i)

                if tgt_name == obj_name:
                    i += 1
                else:
                    obj_name_idx, = (j for j in xrange(obj.dim(dt,i))
                            if obj.get_dim_name(dt, j) == tgt_name)

                    if i != obj_name_idx:
                        obj = obj.move_dims(dt, i, dt, obj_name_idx, 1)

                    i += 1
            else:
                obj = obj.insert_dims(dt, i, 1)
                obj = obj.set_dim_name(dt, i, tgt_name)
                i += 1

        if i < obj.dim(dt) and not obj_bigger_ok:
            raise ValueError("obj has leftover dimensions in align_spaces()")

    return obj





# vim: foldmethod=marker
