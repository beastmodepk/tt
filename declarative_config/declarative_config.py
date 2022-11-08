#!/usr/bin/python3
"""Takes yaml data for a product listing as a file and executes the appropriate
queries on the database, or generate a yaml file from the database for a given
listing."""
from argparse import ArgumentParser, HelpFormatter, _SubParsersAction
import logging
import sys
import os
import configparser
from cerberus import Validator
import pg
import yaml

# contains the tree id that maps to a given architecture.
# Used only in the tree_prod_map table.
tree_ids_for_given_arches = {
    "i386": 5559,
    "ia64": 5899,
    "aarch64": 51630,
    "ppc": 5901,
    "ppc64": 17097,
    "ppc64le": 46533,
    "s390": 9867,
    "s390x": 5900,
    "x86_64": 5558,
}


class NoListingsFound(Exception):
    """Called when the given input matches no entry in the DB."""


class YamlBadFormat(Exception):
    """Called when the validator fails the passed yaml data."""

    def __init__(self, errors):
        super().__init__()
        self.errors = errors


class NoSubparsersMetavarFormatter(HelpFormatter):
    """From https://stackoverflow.com/questions/11070268"""

    def _format_action(self, action):
        result = super()._format_action(action)
        if isinstance(action, _SubParsersAction):
            # fix indentation on first line
            return "%*s%s" % (self._current_indent, "", result.lstrip())
        return result

    def _format_action_invocation(self, action):
        if isinstance(action, _SubParsersAction):
            # remove metavar and help line
            return ""
        return super()._format_action_invocation(action)

    def _iter_indented_subactions(self, action):
        if isinstance(action, _SubParsersAction):
            try:
                get_subactions = action._get_subactions
            except AttributeError:
                pass
            else:
                # remove indentation
                yield from get_subactions()
        else:
            yield from super()._iter_indented_subactions(action)


############################
# DB Interfacing Functions #
############################

# Copied from prod_listings.py
def connect(path="db_connections.conf"):
    """Connect to the database."""
    db_config = configparser.ConfigParser()
    profile = ""

    if os.getenv("PROD_DB") == "true":
        profile = "production"
    elif "CI" in os.environ:
        profile = "ci_test"
    else:
        profile = "local_test"

    db_config.read(path)

    my_db = pg.DB(
        db_config[profile]["DB_NAME"],
        host=db_config[profile]["DB_HOST"],
        user=db_config[profile]["DB_USER"],
        passwd=db_config[profile]["DB_PASSWD"],
    )
    return my_db


def exec_query(query, commit, my_db, print_changes_only):
    """Execute a query."""
    if query.startswith("SELECT"):
        if not print_changes_only:
            logging.info("Executing: " + query)
        result = my_db.query(query).dictresult()
        logging.debug("Query returned: " + str(result))
        return result

    if commit:
        logging.info("Executing:" + query)
        result = my_db.query(query)
        logging.debug("Query returned: " + str(result))
        return result

    logging.info("Would have executed: " + query)


def delete_override(override, commit, my_db, print_changes_only):
    """Delete an override package that wasn't in the yaml file.

    Override should come in as a list whose first item is pkg_name,
    second item is pkg_arch, third item is prod_arch, and fourth item is prod_id."""
    pkg_name, pkg_arch, prod_arch, prod_id, include = (
        override[0],
        override[1],
        override[2],
        override[3],
        override[4],
    )
    query = """DELETE from overrides
    where name = '{0}' and
    pkg_arch = '{1}' and
    product_arch = '{2}' and
    product = {3} and include = '{4}'""".format(
        pkg_name, pkg_arch, prod_arch, prod_id, include
    )
    exec_query(query, commit, my_db, print_changes_only)


def get_product_overrides(prod_id, commit, my_db, print_changes_only):
    """Get the overrides entries for a given product."""
    query = """SELECT * FROM overrides WHERE product = '{0}'""".format(prod_id)
    result = exec_query(query, commit, my_db, print_changes_only)
    return result


# Copied from prod_listings.py
def get_product_id(product, commit, my_db, print_changes_only):
    """Get the id for a given product table entry.

    product should come in as a list whose first item is the label,
    second is version, third is variant, and fourth is allow_source_only."""
    label, version, variant, allow_source_only = (
        product[0],
        product[1],
        product[2],
        product[3],
    )
    query = """SELECT id FROM products
    WHERE label = '{0}'and
    version = '{1}' and
    variant = '{2}' and
    allow_source_only = '{3}'
    order by id""".format(
        label, version, variant, allow_source_only
    )
    products = exec_query(query, commit, my_db, print_changes_only)
    if products:
        return products[0]["id"]
    # The following can only be executed in no-commit mode
    # Where the product listing hasn't previously been inserted.
    logging.info(
        "No entry exists yet, substituting a fake ID of 0. In commit "
        + "mode all occurrences of product ID would use the real ID."
    )
    return 0


def add_product(product, commit, my_db, print_changes_only):
    """Insert into products if the entry is not already there.

    product should come in as a list whose first item is the label,
    second is version, third is variant, and fourth is allow_source_only."""
    label, version, variant, allow_source_only = (
        product[0],
        product[1],
        product[2],
        product[3],
    )
    query = """SELECT exists(
    SELECT * from products
    where label='{0}' and
    version='{1}' and
    variant='{2}' and
    allow_source_only='{3}')""".format(
        label, version, variant, allow_source_only
    )

    result = exec_query(query, commit, my_db, print_changes_only)

    if result[0]["exists"]:
        logging.info(
            """DB already has an entry in products table where
    label='{0}' and
    version='{1}' and
    variant='{2}' and
    allow_source_only='{3}'
    No insert will be executed.""".format(
                label, version, variant, allow_source_only
            )
        )
    else:
        query = """INSERT into products (id, label, version, variant, allow_source_only)
    SELECT nextval('products_id_seq'), '{0}', '{1}', '{2}', '{3}' where not exists (
    SELECT from products
    where label = '{0}' and
    version = '{1}' and
    variant = '{2}' and
    allow_source_only = '{3}')""".format(
            label, version, variant, allow_source_only
        )
        exec_query(query, commit, my_db, print_changes_only)


def add_overrides(
    override,
    commit,
    my_db,
    print_changes_only,
    include=True,
):
    """Insert into overrides if the entry is not already there.

    Override should come in as a list whose first item is pkg_name,
    second item is pkg_arch, third item is prod_arch, and fourth item is prod_id."""
    pkg_name, pkg_arch, prod_arch, prod_id = (
        override[0],
        override[1],
        override[2],
        override[3],
    )
    query = """SELECT exists(
    SELECT * from overrides
    where name='{0}' and
    pkg_arch='{1}' and
    product_arch='{2}' and
    product={3})""".format(
        pkg_name, pkg_arch, prod_arch, prod_id
    )

    result = exec_query(query, commit, my_db, print_changes_only)

    if result[0]["exists"]:
        logging.info(
            """Package listing already exists in overrides table where
    name='{0}' and
    pkg_arch='{1}' and
    product_arch='{2}' and
    product={3}
    No insert will be executed.""".format(
                pkg_name, pkg_arch, prod_arch, prod_id
            )
        )

    else:
        query = """INSERT into overrides
    (name, pkg_arch, product_arch, product, include)
    SELECT '{0}', '{1}', '{2}', {3}, '{4}'""".format(
            pkg_name, pkg_arch, prod_arch, prod_id, include
        )
        exec_query(query, commit, my_db, print_changes_only)


def add_tree_product_mapping(tree_product_mapping, commit, my_db, print_changes_only):
    """Insert into tree_product_mappings the arch offering of a product
    paired with the prod ID if that entry is not already there.

    Tree_product_mapping should come in as a list whose first item is the tree id
    and whose second item is the product id.
    """
    tree_id, prod_id = tree_product_mapping[0], tree_product_mapping[1]
    query = """SELECT exists(
    SELECT * from tree_product_map
    where tree_id='{0}' and
    product_id='{1}')""".format(
        tree_id, prod_id
    )

    result = exec_query(query, commit, my_db, print_changes_only)

    if result[0]["exists"]:
        logging.info(
            """Tree product mapping already exists
    where tree_id='{0}' and
    prod_id='{1}'
    No insert will be executed.""".format(
                tree_id, prod_id
            )
        )

    else:
        query = """INSERT into tree_product_map (tree_id, product_id)
        SELECT '{0}', '{1}'""".format(
            tree_id, prod_id
        )
        exec_query(query, commit, my_db, print_changes_only)


##########################
# Other helper functions #
##########################


def insert_package(
    override, entry, current_packages, commit, my_db, print_changes_only
):
    """Aids process_package_listings() in inserting a package into the DB.
    Inserts entries into the overrides and tree_product_map where appropriate.
    Updates the current packages dictionary, necessary for making proper deletions
    after processing all the packages in the yaml file.

    override should come in as a list where:
    1st item: package name
    2nd item: package architecture
    3rd item: product architecture
    4th item: product ID
    """
    # pkg_name = override[0]
    pkg_arch = override[1]
    prod_arch = override[2]
    prod_id = override[3]
    add_overrides(
        override,
        commit,
        my_db,
        print_changes_only,
        "True",
    )

    entry["pkg_arch"] = pkg_arch
    entry["product_arch"] = prod_arch

    if entry in current_packages:
        current_packages.remove(entry)

    add_tree_product_mapping(
        [tree_ids_for_given_arches.get(prod_arch), prod_id],
        commit,
        my_db,
        print_changes_only,
    )


#############################
# Yaml Processing Functions #
#############################


def validate_data(options):
    """Loads the validation schema and validates
    the given data agaisnt it.
    """
    logging.debug("Loading yaml data from {0}".format(options.filepath))
    with open(options.filepath, encoding="ascii") as path:
        data = yaml.load(path, Loader=yaml.FullLoader)

    logging.debug("Loading data validator from {0}".format(options.schemapath))
    with open(options.schemapath, encoding="ascii") as yaml_schema_file:
        yaml_schema = yaml.load(yaml_schema_file, Loader=yaml.FullLoader)

    yaml_validator = Validator(yaml_schema)

    logging.debug("Validating...")
    # Validate prod listing data
    if not yaml_validator.validate(data):
        logging.critical("The yaml data failed validation against the schema.")
        logging.critical("No database queries were executed.")
        logging.debug(yaml_validator.errors)
        raise YamlBadFormat(yaml_validator.errors)

    logging.info("Pass")


def generate_yaml(options):
    """Connects to the database, queries the requested information,
    stores in a Python dictionary structure and dumps to the specified yaml file.
    Takes as input the parsed arguments from the commandline.
    """

    if not os.path.exists(os.path.dirname(options.filepath)):
        os.mkdir(os.path.dirname(options.filepath))

    logging.info("Connecting to DB and querying products and overrides...")
    my_db = connect()

    try:
        query = """select * from products
        where label = '{0}' and version = '{1}' and variant = '{2}'""".format(
            options.product, options.version, options.variant
        )
        logging.debug("Executing: " + query)
        products = my_db.query(query).getresult()
        if not products:
            raise NoListingsFound

        prod_ids = []
        for prod in products:
            prod_ids.append(str(prod[0]))
        prod_ids = "(" + ", ".join(prod_ids) + ")"
        logging.debug("Product ID's found: " + prod_ids)

        query = """select name, pkg_arch, product_arch, product from overrides
        where product in {0}""".format(
            prod_ids
        )
        logging.debug("Executing: " + query)
        overrides = (my_db.query(query)).getresult()
        logging.debug("Done.")

        my_db.close()

        logging.debug("Creating Python dictionary from the collected data...")
        yaml_data = {}

        # Here I use the 0th result to get product version and variant, but each
        # result has the same. These match the passed in arguments too, so there
        # Are many ways to reference the same identifiers.
        prod_name = products[0][1]
        prod_version = float(products[0][2])
        prod_variant = products[0][3]
        prod_allow_source_only = products[0][4]

        yaml_data = {
            "product_name": prod_name,
            "version": prod_version,
            "variant": prod_variant,
            "allow_source_only": prod_allow_source_only,
            "packages": {},
        }

        yaml_package_listings = yaml_data["packages"]

        for package in overrides:
            pkg_name = package[0]
            pkg_arch = package[1]
            prod_arch = package[2]

            if pkg_name not in yaml_package_listings:
                yaml_package_listings[pkg_name] = {}

            if pkg_arch == prod_arch:
                if "arch" not in yaml_package_listings[pkg_name]:
                    yaml_package_listings[pkg_name]["arch"] = []
                yaml_package_listings[pkg_name]["arch"].append(pkg_arch)
            elif pkg_arch == "src":
                if "src" not in yaml_package_listings[pkg_name]:
                    yaml_package_listings[pkg_name]["src"] = []
                yaml_package_listings[pkg_name]["src"].append(prod_arch)
            elif pkg_arch == "noarch":
                if "noarch" not in yaml_package_listings[pkg_name]:
                    yaml_package_listings[pkg_name]["noarch"] = []
                yaml_package_listings[pkg_name]["noarch"].append(prod_arch)
            elif pkg_arch not in ("src", "noarch", prod_arch):
                if "multilib" not in yaml_package_listings[pkg_name]:
                    yaml_package_listings[pkg_name]["multilib"] = []
                yaml_package_listings[pkg_name]["multilib"].append(
                    {pkg_arch: prod_arch}
                )

        # Remove the packages category altogether if there are zero packages listed
        if not yaml_package_listings:
            yaml_data.pop("packages")

        logging.debug("Done.")
        logging.info("Dumping to file...")
        with open(options.filepath, "w", encoding="ascii") as yaml_file:
            yaml_file.write("---\n")
            yaml.dump(yaml_data, yaml_file, sort_keys=False)
        logging.info("Success! Yaml data is stored in {0}.".format(options.filepath))

    except NoListingsFound:
        logging.critical(
            """The database has no row for {0}, version {1}, and variant {2}.
            No file was written.""".format(
                options.product, options.version, options.variant
            )
        )
        sys.exit(1)
    except Exception as _e:
        logging.exception(_e)
        sys.exit(1)


def process_package_listings(packages, prod_id, commit, my_db, print_changes_only):
    """
    A helper function for process_prod_listings.
    Takes as input a section of already-parsed yaml data that
    contains the packages included in a product/version/variant
    and generates appropriate commands for the DB.

    First, get all the packages under the id from the db as a list.
    Then, iterate over the yaml dataset (what we want to be the final
    dataset in the db as well). If the current package is not already
    in the db, just add it. if the item is in both sets, then it is
    already in the db, so remove it from the db list. After iteration,
    All that's left in the db list are items that should no longer be in
    the db, so iterate over them and execute remove queries.

    packages comes in as a list of dictionaries whose keys are package names
        and whose values are lists of pkg archs.

    prod_id is the ID of the product table entry that corresponds
        to new overrides table entries.
    """
    current_packages = get_product_overrides(prod_id, commit, my_db, print_changes_only)
    # ^Contains entries that may or may not be in yaml data.
    for pkg_name in packages:
        entry = {"name": pkg_name, "product": prod_id, "include": True}

        if "noarch" in packages.get(pkg_name):
            for prod_arch in packages.get(pkg_name).get("noarch", []):
                insert_package(
                    [pkg_name, "noarch", prod_arch, prod_id],
                    entry,
                    current_packages,
                    commit,
                    my_db,
                    print_changes_only,
                )

        if "src" in packages.get(pkg_name):
            # If src is prsent, it is a list of prod arches for which the package
            # is being offered as source.
            for prod_arch in packages.get(pkg_name).get("src", []):
                insert_package(
                    [pkg_name, "src", prod_arch, prod_id],
                    entry,
                    current_packages,
                    commit,
                    my_db,
                    print_changes_only,
                )

        if "arch" in packages.get(pkg_name):
            for pkg_arch in packages.get(pkg_name).get("arch", []):
                insert_package(
                    [pkg_name, pkg_arch, pkg_arch, prod_id],
                    entry,
                    current_packages,
                    commit,
                    my_db,
                    print_changes_only,
                )

        if "multilib" in packages.get(pkg_name):
            for offering in packages.get(pkg_name).get("multilib", []):
                pkg_arch = list(offering.keys())[0]
                prod_arch = list(offering.values())[0]

                insert_package(
                    [pkg_name, pkg_arch, prod_arch, prod_id],
                    entry,
                    current_packages,
                    commit,
                    my_db,
                    print_changes_only,
                )

    # At this point there are only items that are NOT in the yaml data
    for override in current_packages:
        pkg_name = override.get("name")
        pkg_arch = override.get("pkg_arch")
        prod_arch = override.get("product_arch")
        product = prod_id
        include = "True"
        delete_override(
            [pkg_name, pkg_arch, prod_arch, product, include],
            commit,
            my_db,
            print_changes_only,
        )


def process_prod_listings(options):
    """Opens the yaml file, validates the data, and parses it, executing
    appropriate queries on the database. Takes as input the parsed arguments
    from the commandline.
    """
    try:
        if not options.commit:
            logging.info(
                "The --commit option was not specified, "
                + "so the database will not be modified."
            )
        # Load files
        logging.debug("Loading yaml data from {0}".format(options.filepath))
        with open(options.filepath, encoding="ascii") as yaml_file:
            yaml_data = yaml.load(yaml_file, Loader=yaml.FullLoader)

        validate_data(options)

        # Connect to DB
        logging.debug("Connecting to the database")
        my_db = connect()

        logging.debug("Processing data")
        prod_name = yaml_data.get("product_name")
        version = yaml_data.get("version")
        variant = yaml_data.get("variant")
        allow_source_only = yaml_data.get("allow_source_only")
        packages = yaml_data.get("packages", [])

        # Adding product entry must be done here to get the key id
        # which is used for packages (in overrides table) immediately after
        add_product(
            [prod_name, version, variant, allow_source_only],
            options.commit,
            my_db,
            options.print_changes_only,
        )
        prod_id = get_product_id(
            [prod_name, version, variant, allow_source_only],
            options.commit,
            my_db,
            options.print_changes_only,
        )

        logging.debug("Got a product ID of {0}".format(prod_id))

        process_package_listings(
            packages, prod_id, options.commit, my_db, options.print_changes_only
        )

        my_db.close()

        if not options.commit:
            logging.info(
                "Did not run any INSERT or DELETE database queries. Nothing "
                + "was changed. Rerun with --commit to apply the above changes."
            )

    except YamlBadFormat as _e:
        logging.critical("The yaml data failed validation against the schema.")
        logging.critical("No database queries were executed.")
        logging.debug(_e.errors)
        sys.exit(1)
    except Exception as _e:
        logging.exception(_e)
        sys.exit(1)


def main(args):
    """Either read in data containing the variants with their packages and architectures
    for one product and version, stored as a yaml data file, validate it against a
    specified schema, and execute queries to add the appropriate entries in
    ComposedDB in the products, overrides, tree_product_map tables, or read in data from
    the db and store as a yaml file.

    This automates the process so developers don't have to manually edit the db.

    The script can be run as a bash file, in which case incoming arguments come from
    the commandline.
    """
    parser = ArgumentParser(
        description="""
    Takes a yaml file containing a product listing and updates the database with
    the appropriate entries, or reads a product listing from the database and
    stores to a yaml file.""",
        formatter_class=NoSubparsersMetavarFormatter,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help="Send all messages to standard output.",
        action="store_true",
    )

    # Verbose will send down to logging.debug messages, default is just logging.info

    subparsers = parser.add_subparsers(dest="command", title="command")

    # Generate-specific commands
    parse_generate = subparsers.add_parser(
        "generate",
        help="Generate a yaml file for a specific product listing from the DB",
    )
    parse_generate.add_argument(
        "filepath", help="The path to the file to which yaml data will be written."
    )
    prod_spec_options = parse_generate.add_argument_group(
        "Product specification options"
    )
    prod_spec_options.add_argument(
        "--product", metavar="", help="The product name.")
    prod_spec_options.add_argument(
        "--version", metavar="", help="The version of the product.")
    prod_spec_options.add_argument(
        "--variant", metavar="", help="The variant of the version.")

    parse_generate.set_defaults(func=generate_yaml)

    # Insertion-specific commands
    parse_insert = subparsers.add_parser(
        "insert", help="Insert a product listing into the DB from a yaml file"
    )

    parse_insert.add_argument(
        "filepath",
        help="The path to the .yaml file containing product "
        + "info to be stored in the database.",
    )
    parse_insert.add_argument(
        "--schemapath",
        help="Optionally specify the path to the .yaml file containing the "
        + "validation schema to evaluate the file.",
        default="yaml_schema.yaml",
        metavar="",
    )
    parse_insert.add_argument(
        "-c",
        "--commit",
        help="Commit changes. If not specified, the database is not altered.",
        action="store_true",
    )
    parse_insert.add_argument(
        "--print-changes-only",
        help="Only prints out non-SELECT queries.",
        action="store_true",
    )
    parse_insert.add_argument(
        "-v",
        "--verbose",
        help="Send all messages to standard output.",
        action="store_true",
    )

    parse_insert.set_defaults(func=process_prod_listings)

    # Validate only
    parse_validate = subparsers.add_parser(
        "validate",
        help="Validate a yaml file against the specified schema",
    )

    parse_validate.add_argument(
        "filepath",
        help="The path to the .yaml file containing product info.",
    )
    parse_validate.add_argument(
        "--schemapath",
        help="Optionally specify the path to the .yaml file containing the "
        + "validation schema to evaluate the file.",
        default="yaml_schema.yaml",
        metavar="",
    )
    parse_validate.add_argument(
        "-v",
        "--verbose",
        help="Send all messages to standard output.",
        action="store_true",
    )

    parse_validate.set_defaults(func=validate_data)

    options = parser.parse_args(args)

    if options.verbose:
        logging.basicConfig(encoding="utf-8", level=logging.DEBUG)
    else:
        logging.basicConfig(encoding="utf-8", level=logging.INFO)

    options.func(options)


if __name__ == "__main__":
    main(sys.argv[1:])
