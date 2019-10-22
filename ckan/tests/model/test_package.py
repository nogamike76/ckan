# encoding: utf-8

import pytest

from ckan import model
from ckan.tests import factories


@pytest.mark.usefixtures("clean_db")
def test_create():
    # Demonstrate creating a package.
    #
    # In practice this is done by a combination of:
    # * ckan.logic.action.create:package_create
    # * ckan.lib.dictization.model_save.py:package_dict_save
    # etc

    model.repo.new_revision()

    pkg = model.Package(name=u"test-package")
    pkg.notes = u"Some notes"
    pkg.author = u"bob"
    pkg.license_id = u"odc-by"

    model.Session.add(pkg)
    model.Session.commit()
    model.Session.remove()

    pkg = model.Package.by_name(u"test-package")
    assert pkg.notes == u"Some notes"
    assert pkg.author == u"bob"
    assert pkg.license_id == u"odc-by"
    assert pkg.license.title == u"Open Data Commons Attribution License"


@pytest.mark.usefixtures("clean_db")
def test_update():
    dataset = factories.Dataset()
    pkg = model.Package.by_name(dataset["name"])

    model.repo.new_revision()
    pkg.author = u"bob"
    model.Session.commit()
    model.Session.remove()

    pkg = model.Package.by_name(dataset["name"])
    assert pkg.author == u"bob"


@pytest.mark.usefixtures("clean_db")
def test_delete():
    group = factories.Group()
    dataset = factories.Dataset(
        groups=[{
            u"id": group["id"]
        }],
        tags=[{
            u"name": u"science"
        }],
        extras=[{
            u"key": u"subject",
            u"value": u"science"
        }],
    )
    pkg = model.Package.by_name(dataset["name"])

    model.repo.new_revision()
    pkg.delete()
    model.Session.commit()
    model.Session.remove()

    pkg = model.Package.by_name(dataset["name"])
    assert pkg.state == u"deleted"
    # it is removed from the group
    group = model.Group.get(group["id"])
    assert [p.name for p in group.packages()] == []
    # other related objects don't change
    package_extra = model.Session.query(model.PackageExtra).all()[0]
    assert package_extra.state == u"active"
    package_tag = model.Session.query(model.PackageTag).all()[0]
    assert package_tag.state == u"active"
    tag = model.Session.query(model.Tag).all()[0]
    assert [p.name for p in tag.packages] == [dataset["name"]]


@pytest.mark.usefixtures("clean_db")
def test_purge():
    org = factories.Organization()
    group = factories.Group()
    dataset = factories.Dataset(
        resources=[{
            u"url": u"http://example.com/image.png",
            u"format": u"png",
            u"name": u"Image 1",
        }],
        tags=[{
            u"name": u"science"
        }],
        extras=[{
            u"key": u"subject",
            u"value": u"science"
        }],
        groups=[{
            u"id": group["id"]
        }],
        owner_org=org["id"],
    )
    pkg = model.Package.by_name(dataset["name"])

    model.repo.new_revision()
    pkg.purge()
    model.Session.commit()
    model.Session.remove()

    assert not model.Session.query(model.Package).all()
    # the purge cascades to some objects
    assert not model.Session.query(model.PackageExtra).all()
    assert not model.Session.query(model.PackageTag).all()
    assert not model.Session.query(model.Resource).all()
    # org remains, just not attached to the package
    org = model.Group.get(org["id"])
    assert org.packages() == []
    # tag object remains, just not attached to the package
    tag = model.Session.query(model.Tag).all()[0]
    assert tag.packages == []
    # group object remains, just not attached to the package
    group = model.Group.get(group["id"])
    assert group.packages() == []
