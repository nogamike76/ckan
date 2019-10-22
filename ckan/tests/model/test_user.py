# encoding: utf-8

import os

import hashlib
import pytest
from passlib.hash import pbkdf2_sha512
from six import text_type

import ckan.model as model
import ckan.tests.factories as factories


def _set_password(password):
    """Copy of the old password hashing function

    This is needed to create old password hashes in the tests
    """
    if isinstance(password, text_type):
        password_8bit = password.encode("ascii", "ignore")
    else:
        password_8bit = password

    salt = hashlib.sha1(os.urandom(60))
    hash = hashlib.sha1(password_8bit + salt.hexdigest())
    hashed_password = salt.hexdigest() + hash.hexdigest()

    if not isinstance(hashed_password, text_type):
        hashed_password = hashed_password.decode("utf-8")
    return hashed_password


@pytest.mark.usefixtures("clean_db")
def test_upgrade_from_sha():
    user = factories.User()
    user_obj = model.User.by_name(user["name"])

    # setup our user with an old password hash
    old_hash = _set_password("testpass")
    user_obj._password = old_hash
    user_obj.save()

    user_obj.validate_password("testpass")
    assert old_hash != user_obj.password
    assert pbkdf2_sha512.identify(user_obj.password)
    assert pbkdf2_sha512.verify("testpass", user_obj.password)


@pytest.mark.usefixtures("clean_db")
def test_upgrade_from_sha_with_unicode_password():
    user = factories.User()
    password = u"testpassword\xc2\xa0"
    user_obj = model.User.by_name(user["name"])

    # setup our user with an old password hash
    old_hash = _set_password(password)
    user_obj._password = old_hash
    user_obj.save()

    assert user_obj.validate_password(password)
    assert old_hash != user_obj.password
    assert pbkdf2_sha512.identify(user_obj.password)
    assert pbkdf2_sha512.verify(password, user_obj.password)

    # check that we now allow unicode characters
    assert not pbkdf2_sha512.verify("testpassword", user_obj.password)


@pytest.mark.usefixtures("clean_db")
def test_upgrade_from_sha_with_wrong_password_fails_to_upgrade():
    user = factories.User()
    password = u"testpassword"
    user_obj = model.User.by_name(user["name"])

    old_hash = _set_password(password)
    user_obj._password = old_hash
    user_obj.save()

    assert not user_obj.validate_password("wrongpass")
    assert old_hash == user_obj.password
    assert not pbkdf2_sha512.identify(user_obj.password)


@pytest.mark.usefixtures("clean_db")
def test_upgrade_from_pbkdf2_with_less_rounds():
    """set up a pbkdf key with less than the default rounds

    If the number of default_rounds is increased in a later version of
    passlib, ckan should upgrade the password hashes for people without
    involvement from users"""
    user = factories.User()
    password = u"testpassword"
    user_obj = model.User.by_name(user["name"])

    # setup hash with salt/rounds less than the default
    old_hash = pbkdf2_sha512.encrypt(password, salt_size=2, rounds=10)
    user_obj._password = old_hash
    user_obj.save()

    assert user_obj.validate_password(password.encode("utf-8"))
    # check that the hash has been updated
    assert old_hash != user_obj.password
    new_hash = pbkdf2_sha512.from_string(user_obj.password)

    assert pbkdf2_sha512.default_rounds > 10
    assert pbkdf2_sha512.default_rounds == new_hash.rounds

    assert pbkdf2_sha512.default_salt_size, 2
    assert pbkdf2_sha512.default_salt_size == len(new_hash.salt)
    assert pbkdf2_sha512.verify(password, user_obj.password)


@pytest.mark.usefixtures("clean_db")
def test_upgrade_from_pbkdf2_fails_with_wrong_password():
    user = factories.User()
    password = u"testpassword"
    user_obj = model.User.by_name(user["name"])

    # setup hash with salt/rounds less than the default

    old_hash = pbkdf2_sha512.encrypt(password, salt_size=2, rounds=10)
    user_obj._password = old_hash
    user_obj.save()

    assert not user_obj.validate_password("wrong_pass")
    # check that the hash has _not_ been updated
    assert old_hash == user_obj.password


@pytest.mark.usefixtures("clean_db")
def test_pbkdf2_password_auth():
    user = factories.User()
    password = u"testpassword"
    user_obj = model.User.by_name(user["name"])

    user_obj._set_password(password)
    user_obj.save()
    assert user_obj.validate_password(password)


@pytest.mark.usefixtures("clean_db")
def test_pbkdf2_password_auth_unicode():
    user = factories.User()
    password = u"testpassword\xc2\xa0"
    user_obj = model.User.by_name(user["name"])
    user_obj._set_password(password)
    user_obj.save()

    assert user_obj.validate_password(password)
