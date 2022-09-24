import os

import jschema_to_python.utilities as util
from jschema_to_python.init_file_generator import InitFileGenerator
from jschema_to_python.class_generator import ClassGenerator


class ObjectModelModuleGenerator:
    def __init__(self, args):
        self.output_directory = args.output_directory
        self.force = args.force
        self.module_name = args.module_name
        self.root_schema = self.read_schema(args.schema_path)
        self.code_gen_hints = self.read_code_gen_hints(args.hints_file_path)
        self.root_class_name = args.root_class_name

        self.gen = Generator(self.root_schema, self.code_gen_hints, self.output_directory)

    def generate(self):
        util.create_directory(self.output_directory, self.force)
        self.generate_root_class()
        self.gen.generate_definition_classes()
        self.generate_init_file()

    def generate_init_file(self):
        init_file_generator = InitFileGenerator(
            self.module_name,
            self.root_schema,
            self.root_class_name,
            self.output_directory,
        )
        init_file_generator.generate()

    def generate_root_class(self):
        class_generator = ClassGenerator(
            self.root_schema,
            self.root_class_name,
            self.code_gen_hints,
            self.output_directory,
            self.gen,
        )
        class_generator.generate()

    # def generate_definition_classes(self):
        # definition_schemas = self.root_schema.get("definitions")
        # if definition_schemas:
            # for key in definition_schemas:
                # self.gen.generate_definition_class(key, definition_schemas[key])

    # def generate_definition_class(self, definition_key, definition_schema):
        # class_name = util.capitalize_first_letter(definition_key)
        # class_generator = ClassGenerator(
            # definition_schema, class_name, self.code_gen_hints, self.output_directory,
            # self.gen,
        # )
        # class_generator.generate()

    def read_schema(self, schema_path):
        if not os.path.exists(schema_path):
            util.exit_with_error("schema file {} does not exist", schema_path)

        return util.unpickle_file(schema_path)

    def read_code_gen_hints(self, hints_file_path):
        if not hints_file_path:
            return None

        if not os.path.exists(hints_file_path):
            util.exit_with_error(
                "code generation hints file {} does not exist", hints_file_path
            )

        return util.unpickle_file(hints_file_path)


class Generator:
    def __init__(self, schema, code_gen_hints, output_directory):
        self.root_schema = schema
        self.code_gen_hints = code_gen_hints
        self.output_directory = output_directory

        self.mapping = {}
        self.being_defined = {}

    def generate_definition_classes(self):
        definition_schemas = self.root_schema.get("definitions")
        if definition_schemas:
            for key in definition_schemas:
                self.generate_definition_class(key, definition_schemas[key])

    def generate_definition_class(self, definition_key, definition_schema):
        if definition_key in self.mapping:
            return


        class_name = util.capitalize_first_letter(definition_key)
        self.being_defined[definition_key] = class_name
        print(" / ".join(self.being_defined))

        class_generator = ClassGenerator(
            definition_schema, class_name, self.code_gen_hints, self.output_directory,
            self,
        )
        class_generator.generate()

        self.mapping[definition_key] = class_generator
        self.being_defined.pop(definition_key)

    def get_definition(self, key):
        if key in self.being_defined:
            return self.being_defined[key]

        try:
            return self.mapping[key]
        except KeyError:
            pass

        definition_schemas = self.root_schema.get("definitions")

        self.generate_definition_class(key, definition_schemas[key])
        return self.mapping[key]
