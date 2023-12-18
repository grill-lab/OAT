import os
import argparse
import sys
from pathlib import Path

# Parses each of the requirements.txt files and checks that
# every package with multiple entries is pinned to the same
# version.

SERVICES = [
    'builder',
    'dashboard',
    'external_functionalities',
    'functionalities',
    'oat_common',
    'local_client',
    'neural_functionalities',
    'offline',
    'orchestrator',
    'tester',
    'sphinx_docs',
]

OAT_PATH = Path(os.path.dirname(__file__)).parent.parent.parent


def parse_service_requirements(repo_path, service_name):
    """
    Parse the <OAT repo>/<name>/requirements.txt file and build a
    dict of package names and versions.

    Arguments:
        repo_path: base path of OAT repo (str)
        service_name: OAT service name (str)

    Returns:
        a dict with entries {package_name: package_version} (both str)
    """
    version_info = {}
    with open(os.path.join(repo_path, service_name, 'requirements.txt'), 'r') as rf:
        reqs = rf.readlines()
        for req in reqs:

            # skip comments, lines starting with "--" (pip commands),
            # empty lines, ...
            req = req.strip()
            if req.startswith('#') or req.startswith('--') or len(req) == 0:
                continue

            # there are a couple of current entries that will be flagged up by
            # this:
            #   - functionalities: downloads a spacy model
            #   - neural functionalities: currently uses git+https://github.com/openai/CLIP.git
            if '==' not in req:
                print(f'Warning: unpinned requirement: {service_name} : {req.strip()}')
            else:
                package, version = req.strip().split('==')
                version_info[package] = version

    return version_info


def check_deps(all_service_requirements):
    """
    Perform a simple consistency check on the collected set of service requirements.

    This should catch any instances where packages are defined in 2 or more 
    requirements.txt files with different pinned versions.
    """

    oat_requirements = {}
    results = {}

    for service_name, service_requirements in all_service_requirements.items():
        for package, version in service_requirements.items():
            if package not in oat_requirements:
                oat_requirements[package] = (version, service_name)
            else:
                existing_version, existing_service = oat_requirements[package]
                if existing_version != version:
                    if package not in results:
                        results[package] = [(existing_service, existing_version)]
                    results[package].append((service_name, version))

    if len(results) == 0:
        print('No problems found')
        return 0

    print(f'Found {len(results)} package problems\n')
    for package in results.keys():
        print(f'{package}')
        for (service, version) in results[package]:
            print(f'   - {service} has version {version}')

    return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--find-package', required=False,
                        help='Just check if a package already exists in any of the requirements.txt files')
    args = parser.parse_args()

    service_reqs = {s: parse_service_requirements(OAT_PATH, s) for s in SERVICES}
    print('')

    # if we just want to check for a package
    if args.find_package is not None:
        for service, requirements in service_reqs.items():
            if args.find_package in requirements:
                print(f'{args.find_package} found in {service}: {args.find_package}=={requirements[args.find_package]}')
        sys.exit(0)

    sys.exit(check_deps(service_reqs))
