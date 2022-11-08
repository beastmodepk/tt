# Notes

Brew is the build site  
* tags: buckets to organize builds
* packages: sort of defines a component
* a build is a collection of rpm's, architecture sorted, named with (NVR: name version release)
  
Errata: releases in advisories (repo mapping)
*  One build per advisory for RHEL
*  For all else, whole release into an advisory
*  Advisories are managed in Errata (contain builds and designate where they go)
*  Builds tab has a list of the builds for an advisory
    *  Shows RPM's in each build
    * Errata shows where an rpm in the build will go, Brew can't know
    * Where an rpm will go is called a variant
    
Product listing: maps the two

In Compose DB in products table, id, label, version, variant, allow_source_only
  * ID is important
  * There is an overrides table which correspond to those ID's
     * product = ID
     * name, pkg_arch, product_arch, product, include
    
  * To connect: `ssh rcm-dev.app.eng.bos.redhat.com`
  
    `psql -h compose-db-01.engineering.redhat.com compose compose_rw`  
    (for ~/.bashrc):
      * `alias prodlist="psql -h compose-db-01.engineering.redhat.com compose compose_rw"`
  * password is compose :))))))
  * \q is quit or ctrl+d
  * from rcm-dev: compose location is `/mnt/redhat/rhel-8/rel-eng/`
    
only use the python `prod-list` script for connecting on the host  

To run the prod-listings, do `./prod-listings` to use Bash  

If a package has a src offering at all, it has it for every architecture for which it was also written, like if there is an x8664 offering and the src is also offered it's for sure offered for x8664  

tree table has placeholders for architectures and tree_product_map has a tree id and product id mapping, so add that after prod listing

Q's for Andrew:
1. `allow_source_only` data in compose directory? where?
2. `include` field in `overrides`? Where is that in a compose
3. How to know what should go to the `tree_product_map`? By default script already inserts based on what it finds

Can run on a jenkins job

will use comose host

update schema

use jenkins

from productmd.compose import Compose
compose = Compose("/path/to/compose")

from functools import partial
pdir = partial(print, sep="\n")
pdir(*dir(compose))

DOCUMENT THIS: can't use postgres:latest super often, there's a usage limit (100 per 6 hours)