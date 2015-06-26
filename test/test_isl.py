from __future__ import division, print_function

__copyright__ = "Copyright (C) 2011-15 Andreas Kloeckner"

__license__ = """
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import islpy as isl


def test_basics():
    dt = isl.dim_type

    ctx = isl.Context()
    space = isl.Space.create_from_names(ctx, set=["a", "b"])

    bset = (isl.BasicSet.universe(space)
            .add_constraint(isl.Constraint.eq_from_names(
                space, {"a": -1, "b": 2}))
            .add_constraint(isl.Constraint.ineq_from_names(
                space, {"a": 1, 1: -10}))
            .add_constraint(isl.Constraint.ineq_from_names(
                space, {"a": -1, 1: 42}))
            .project_out(dt.set, 1, 1))

    bset2 = isl.BasicSet(  # noqa
            "{[i] : exists (a : i = 2a and i >= 10 and i <= 42)}",
            context=ctx)

    points = []
    bset.foreach_point(points.append)

    for pt in points:
        print(pt)


def test_error_on_invalid_index():
    ctx = isl.Context()
    my_set = isl.Set("{ [k, l] : 3l >= -k and 3l <= 10 - k "
                   "and k >=0 and k <= 2 }", context=ctx)
    p = my_set.sample_point()
    try:
        p.get_coordinate_val(isl.dim_type.set, 99999999)
    except isl.Error:
        pass
    else:
        assert False


def test_pwqpoly():
    def term_handler(term):
        print(term.get_coefficient_val())

    def piece_handler(set, qpoly):
        qpoly.foreach_term(term_handler)

    pwqp = isl.PwQPolynomial('[n] -> { n }')
    pwqp.foreach_piece(piece_handler)


def no_test_id_user():
    ctx = isl.Context()
    foo = isl.Id("foo", context=ctx)  # noqa
    t = (1, 2)
    bar = isl.Id("bar", t, context=ctx)

    assert bar.user is t


def test_val():
    for src in [17, "17"]:
        v = isl.Val(src)
        print(v)
        assert v == 17
        assert v.to_python() == 17


def test_pickling():
    instances = [
            isl.Aff("[n] -> { [(-1 - floor((-n)/4))] }"),
            isl.PwAff("[n] -> { [(0)] : n <= 4 and n >= 1; "
                "[(-1 + n - floor((3n)/4))] : n >= 5 }"),
            isl.BasicSet("[n] -> {[i,j,k]: i<=j + k and (exists m: m=j+k) "
                "and n mod 5 = 17}"),
            isl.Set("[n] -> {[i,j,k]: (i<=j + k and (exists m: m=j+k)) or (k=j)}")
            ]

    from pickle import dumps, loads
    for inst in instances:
        inst2 = loads(dumps(inst))

        assert inst.space == inst2.space
        assert inst.is_equal(inst2)


def test_get_id_dict():
    print(isl.Set("[a] -> {[b]}").get_id_dict(isl.dim_type.param))


def test_get_coefficients_by_name():
    my_set = isl.BasicSet("{ [k, l] : 3l >= -k and 3l <= 10 - k "
                   "and k >=0 and k <= 2 }")

    for c in my_set.get_constraints():
        print(c.get_coefficients_by_name())


def test_count_brick_ish():
    a = isl.BasicSet("[n] -> {[i,j]: 0<= i < n and 0<= j < n and j<= i}")

    def count(bset):
        result = 1

        for i in range(bset.dim(isl.dim_type.set)):
            dmax = bset.dim_max(i)
            dmin = bset.dim_min(i)

            length = isl.PwQPolynomial.from_pw_aff(dmax - dmin + 1)

            result = result * length

        return result

    counts = [count(a)]

    if hasattr(a, "card"):
        counts.append(a.card())

    for pwq in counts:
        print("EVAL", pwq, "=", pwq.eval_with_dict(dict(n=10)))


def test_eval_pw_qpolynomial():
    pwaff = isl.PwAff("[n] -> { [(0)] : n <= 4 and n >= 1; "
        "[(-1 + n - floor((3n)/4))] : n >= 5 }")

    pwq = isl.PwQPolynomial.from_pw_aff(pwaff)

    pwq.eval_with_dict(dict(n=10))


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        exec(sys.argv[1])
    else:
        from py.test.cmdline import main
        main([__file__])
