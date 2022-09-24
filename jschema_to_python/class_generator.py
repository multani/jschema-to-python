import io
import sys
from jschema_to_python.python_file_generator import PythonFileGenerator
import jschema_to_python.utilities as util


class ClassGenerator(PythonFileGenerator):
    def __init__(self, class_schema, class_name, code_gen_hints, output_directory, gen):
        super(ClassGenerator, self).__init__(output_directory)
        self.class_schema = class_schema
        self.required_property_names = class_schema.get("required")
        if self.required_property_names:
            self.required_property_names.sort()
        self.class_name = class_name
        self.class_module_name = util.class_name_to_private_module_name(self.class_name)
        self.code_gen_hints = code_gen_hints
        self.file_path = self._make_class_file_path()

        self.gen = gen

        self._imports = set()
        self._buffer = "declaration"
        self._buffers = {
            "declaration": io.StringIO(),
            "description": io.StringIO(),
            "body": io.StringIO(),
        }

    def __del__(self):
        sys.stdout = sys.__stdout__

    def write(self, content):
        if content is None:
            content = ""
        content = str(content)
        self._buffers[self._buffer].write(content + "\n")

    def generate(self):
        with open(self.file_path, "w") as self.fp:
            self.write_generation_comment()
            self._write_class_body()
            self._write_class_description()
            self._write_class_declaration()

            self.fp.write(
                self._buffers["declaration"].getvalue() +
                self._buffers["description"].getvalue() +
                self._buffers["body"].getvalue()
            )

    def _make_class_file_path(self):
        return self.make_output_file_path(self.class_module_name + ".py")

    def _write_class_declaration(self):
        self._buffer = "declaration"

        self._imports.add(("attrs", "define"))

        if self._imports:
            for module, class_ in sorted(self._imports):
                self.write(f"from {module} import {class_}")

        self.write("")
        self.write("")  # The black formatter wants two blank lines here.
        self.write("@define()")
        self.write(f"class {self.class_name}:")

    def _write_class_description(self):
        self._buffer = "description"
        description = self.class_schema.get("description")
        if description:
            self.write('    """' + description + '"""')
            self.write("")  # The black formatter wants a blank line here.

    def _write_class_body(self):
        self._buffer = "body"
        property_schemas = self.class_schema["properties"]
        if not property_schemas:
            self.write("    pass")
            return

        schema_property_names = sorted(property_schemas.keys())

        # attrs requires that mandatory attributes be declared before optional
        # attributes.
        if self.required_property_names:
            for schema_property_name in self.required_property_names:
                attrib = self._make_attrib(schema_property_name)
                self.write(attrib)

        for schema_property_name in schema_property_names:
            if self._is_optional(schema_property_name):
                attrib = self._make_attrib(schema_property_name)
                self.write(attrib)

    def _make_attrib(self, schema_property_name):
        python_property_name = self._make_python_property_name_from_schema_property_name(
            schema_property_name
        )

        property_schema = self.class_schema["properties"][schema_property_name]

        type = self._get_type(property_schema)
        if not type:
            print(property_schema, python_property_name)
            assert False
        print(type)

        self._imports.add(("attrs", "field"))
        attrib = f"    {python_property_name} : {type} = field("

        if self._is_optional(schema_property_name):
            default = self._make_default_setter(property_schema)
            if default == "None":
                type = f"Optional[{type}]"
                self._imports.add(("typing", "Optional"))

            attrib = f"{attrib}{default}, "

        attrib = f"{attrib}metadata={{\"schema_property_name\": \"{schema_property_name}\"}})"

        return attrib

    def _get_type(self, property_schema):
        type = property_schema.get("type")
        if type:
            if type == "string":
                return "str"
            elif type == "integer":
                return "int"
            elif type == "boolean":
                return "bool"
            elif type == "number":
                return "float"
            elif type == "array":
                items = property_schema["items"]
                subtype = self._get_type(items)
                return f"list[{subtype}]"
            elif type == "object":
                props = property_schema["additionalProperties"]
                if "type" in props or "$ref" in props:
                    subtype = self._get_type(props)
                    return f"dict[str, {subtype}]"
                return
            else:
                return

        elif property_schema.get("enum"):
            return "str" # TODO

        elif property_schema.get("$ref"):
            ref = property_schema["$ref"]
            prefix = "#/definitions/"
            assert ref.startswith(prefix)
            key = ref[len(prefix):]

            def_ = self.gen.get_definition(key)
            if isinstance(def_, str):
                return f'"{def_}"'

            self._imports.add((
                f".{def_.class_module_name}",
                def_.class_name,
            ))
            return def_.class_name

    def _is_optional(self, schema_property_name):
        return (
            not self.required_property_names
            or schema_property_name not in self.required_property_names
        )

    def _make_default_setter(self, property_schema):
        initializer = self._make_initializer(property_schema)
        return str(initializer)

    def _make_initializer(self, property_schema):
        default = property_schema.get("default")
        type = property_schema.get("type")
        enum = property_schema.get("enum")

        if type == "array":
            self._imports.add(("attrs", "field"))

            if default is not None and default != []:
                return f"factory=lambda: {str(default)}"
                return f"field(factory=lambda: {str(default)})"

            return "factory=list"
            return "field(factory=list)"

        elif default is not None:
            if type == "string":
                return f'default="{default}"'

            elif enum is not None:
                return f'default="{default}"'

            return f"default={default}"

        return "default=None"

    def _make_python_property_name_from_schema_property_name(
        self, schema_property_name
    ):
        hint_key = self.class_name + "." + schema_property_name
        property_name_hint = self._get_hint(hint_key, "PropertyNameHint")
        if not property_name_hint:
            property_name = schema_property_name
        else:
            property_name = property_name_hint["arguments"]["pythonPropertyName"]
        return util.to_underscore_separated_name(property_name)

    def _get_hint(self, hint_key, hint_kind):
        if not self.code_gen_hints or hint_key not in self.code_gen_hints:
            return None

        hint_array = self.code_gen_hints[hint_key]
        for hint in hint_array:
            if hint["kind"] == hint_kind:
                return hint

        return None
