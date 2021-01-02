from mlprogram.languages.csg import Circle, Difference, Expander, Reference, Rotation


class TestExpander(object):
    def test_expand(self):
        expander = Expander()
        assert expander.expand(Circle(1)) == [Circle(1)]
        assert expander.expand(Rotation(1, Circle(1))) == \
            [Circle(1), Rotation(1, Reference(0))]

        assert expander.expand(Difference(Circle(1),
                                          Circle(1))) == \
            [Circle(1), Circle(1), Difference(Reference(0), Reference(1))]

        assert expander.expand(Difference(Circle(1), Rotation(1, Circle(1)))) == \
            [Circle(1), Circle(1), Rotation(1, Reference(1)),
             Difference(Reference(0), Reference(2))]

    def test_unexpand(self):
        expander = Expander()
        assert expander.unexpand([Circle(1)]) == Circle(1)
        assert expander.unexpand([Rotation(1, Circle(1))]) == \
            Rotation(1, Circle(1))

        assert expander.unexpand(
            [Circle(1), Difference(Circle(1), Reference(0))]
        ) == Difference(Circle(1), Circle(1))

        assert expander.unexpand(
            [Circle(1), Rotation(1, Reference(0)),
             Difference(Circle(1), Reference(1))]
        ) == Difference(Circle(1), Rotation(1, Circle(1)))
