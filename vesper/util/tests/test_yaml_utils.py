from vesper.tests.test_case import TestCase
import vesper.util.yaml_utils as yaml_utils


class YamlUtilsTests(TestCase):


    def test_dump_and_load(self):
        x = {'x': 1, 'y': [1, 2, 3], 'z': {'one': 1}}
        s = yaml_utils.dump(x)
        y = yaml_utils.load(s)
        self.assertEqual(x, y)
        
        
    def test_dump_and_load_with_non_default_flow_style(self):
        x = {'x': 1, 'y': [1, 2, 3], 'z': {'one': 1}}
        s = yaml_utils.dump(x, default_flow_style=False)
        y = yaml_utils.load(s)
        self.assertEqual(x, y)
        
        
    def test_sexagesimal_load(self):
        
        """
        The PyYAML `load` function parses YAML 1.1, in which "12:34:56"
        is the sexagesimal number 12 * 3600 + 34 * 60 + 56 = 45296. We
        use `ruaml_yaml` rather than PyYAML because it can also parse
        YAML 1.2, in which "12:34:56" is simply the string "12:34:56".
        This test checks that `yaml_utils.load` parses its input as we
        would like.
        """
        
        x = yaml_utils.load('12:34:56')
        self.assertEqual(x, '12:34:56')
