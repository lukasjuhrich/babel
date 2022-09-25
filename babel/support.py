"""
    babel.support
    ~~~~~~~~~~~~~

    Several classes and functions that help with integrating and using Babel
    in applications.

    .. note: the code in this module is not used by Babel itself

    :copyright: (c) 2013-2022 by the Babel Team.
    :license: BSD, see LICENSE for more details.
"""
import typing as t

import gettext
import locale

from babel.core import Locale
from babel.dates import format_date, format_datetime, format_time, \
    format_timedelta
from babel.numbers import format_decimal, format_currency, \
    format_percent, format_scientific
from datetime import (
    date as std_date,
    datetime as std_datetime,
    time as std_time,
    timedelta as std_timedelta,
    tzinfo as std_tzinfo,
)


class Format:
    """Wrapper class providing the various date and number formatting functions
    bound to a specific locale and time-zone.

    >>> from babel.util import UTC
    >>> from datetime import date
    >>> fmt = Format('en_US', UTC)
    >>> fmt.date(date(2007, 4, 1))
    u'Apr 1, 2007'
    >>> fmt.decimal(1.2345)
    u'1.234'
    """

    def __init__(self, locale: str, tzinfo: t.Optional[std_tzinfo] = None) -> None:
        """Initialize the formatter.

        :param locale: the locale identifier or `Locale` instance
        :param tzinfo: the time-zone info (a `tzinfo` instance or `None`)
        """
        self.locale = Locale.parse(locale)
        self.tzinfo = tzinfo

    def date(self, date: t.Optional[std_date] = None, format: str = "medium") -> str:
        """Return a date formatted according to the given pattern.

        >>> from datetime import date
        >>> fmt = Format('en_US')
        >>> fmt.date(date(2007, 4, 1))
        u'Apr 1, 2007'
        """
        return format_date(date, format, locale=self.locale)

    def datetime(
        self, datetime: t.Optional[std_datetime] = None, format: str = "medium"
    ) -> str:
        """Return a date and time formatted according to the given pattern.

        >>> from datetime import datetime
        >>> from pytz import timezone
        >>> fmt = Format('en_US', tzinfo=timezone('US/Eastern'))
        >>> fmt.datetime(datetime(2007, 4, 1, 15, 30))
        u'Apr 1, 2007, 11:30:00 AM'
        """
        return format_datetime(datetime, format, tzinfo=self.tzinfo,
                               locale=self.locale)

    def time(
        self,
        time: t.Optional[t.Union[std_time, std_datetime]] = None,
        format: str = "medium",
    ) -> str:
        """Return a time formatted according to the given pattern.

        >>> from datetime import datetime
        >>> from pytz import timezone
        >>> fmt = Format('en_US', tzinfo=timezone('US/Eastern'))
        >>> fmt.time(datetime(2007, 4, 1, 15, 30))
        u'11:30:00 AM'
        """
        return format_time(time, format, tzinfo=self.tzinfo, locale=self.locale)

    def timedelta(
        self,
        delta: std_timedelta,
        granularity: str = "second",
        threshold: float = 0.85,
        format: str = "long",
        add_direction: bool = False,
    ) -> str:
        """Return a time delta according to the rules of the given locale.

        >>> from datetime import timedelta
        >>> fmt = Format('en_US')
        >>> fmt.timedelta(timedelta(weeks=11))
        u'3 months'
        """
        return format_timedelta(delta, granularity=granularity,
                                threshold=threshold,
                                format=format, add_direction=add_direction,
                                locale=self.locale)

    def number(self, number: int) -> str:
        """Return an integer number formatted for the locale.

        >>> fmt = Format('en_US')
        >>> fmt.number(1099)
        u'1,099'
        """
        return format_decimal(number, locale=self.locale)

    def decimal(self, number: float, format: None = None) -> str:
        """Return a decimal number formatted for the locale.

        >>> fmt = Format('en_US')
        >>> fmt.decimal(1.2345)
        u'1.234'
        """
        return format_decimal(number, format, locale=self.locale)

    def currency(self, number, currency):
        """Return a number in the given currency formatted for the locale.
        """
        return format_currency(number, currency, locale=self.locale)

    def percent(self, number: float, format: None = None) -> str:
        """Return a number formatted as percentage for the locale.

        >>> fmt = Format('en_US')
        >>> fmt.percent(0.34)
        u'34%'
        """
        return format_percent(number, format, locale=self.locale)

    def scientific(self, number):
        """Return a number formatted using scientific notation for the locale.
        """
        return format_scientific(number, locale=self.locale)


_TValue = t.TypeVar("_TValue", covariant=True)


class LazyProxy(t.Generic[_TValue]):
    """Class for proxy objects that delegate to a specified function to evaluate
    the actual object.

    >>> def greeting(name='world'):
    ...     return 'Hello, %s!' % name
    >>> lazy_greeting = LazyProxy(greeting, name='Joe')
    >>> print(lazy_greeting)
    Hello, Joe!
    >>> u'  ' + lazy_greeting
    u'  Hello, Joe!'
    >>> u'(%s)' % lazy_greeting
    u'(Hello, Joe!)'

    This can be used, for example, to implement lazy translation functions that
    delay the actual translation until the string is actually used. The
    rationale for such behavior is that the locale of the user may not always
    be available. In web applications, you only know the locale when processing
    a request.

    The proxy implementation attempts to be as complete as possible, so that
    the lazy objects should mostly work as expected, for example for sorting:

    >>> greetings = [
    ...     LazyProxy(greeting, 'world'),
    ...     LazyProxy(greeting, 'Joe'),
    ...     LazyProxy(greeting, 'universe'),
    ... ]
    >>> greetings.sort()
    >>> for greeting in greetings:
    ...     print(greeting)
    Hello, Joe!
    Hello, universe!
    Hello, world!
    """
    __slots__ = ['_func', '_args', '_kwargs', '_value', '_is_cache_enabled', '_attribute_error']
    _value: t.Optional[_TValue]

    def __init__(self, func: t.Callable[..., _TValue], *args, **kwargs) -> None:
        is_cache_enabled = kwargs.pop('enable_cache', True)
        # Avoid triggering our own __setattr__ implementation
        object.__setattr__(self, '_func', func)
        object.__setattr__(self, '_args', args)
        object.__setattr__(self, '_kwargs', kwargs)
        object.__setattr__(self, '_is_cache_enabled', is_cache_enabled)
        object.__setattr__(self, '_value', None)
        object.__setattr__(self, '_attribute_error', None)

    @property
    def value(self) -> _TValue:
        if self._value is None:
            try:
                value = self._func(*self._args, **self._kwargs)
            except AttributeError as error:
                object.__setattr__(self, '_attribute_error', error)
                raise

            if not self._is_cache_enabled:
                return value
            object.__setattr__(self, '_value', value)
        return t.cast(_TValue, self._value)

    def __contains__(self, key):
        return key in self.value  # type: ignore

    def __bool__(self):
        return bool(self.value)

    def __dir__(self):
        return dir(self.value)

    def __iter__(self):
        return iter(self.value)  # type: ignore

    def __len__(self):
        return len(self.value)  # type: ignore

    def __str__(self) -> str:
        return str(self.value)

    def __add__(self, other):
        return self.value + other  # type: ignore

    def __radd__(self, other):
        return other + self.value  # type: ignore

    def __mod__(self, other):
        return self.value % other

    def __rmod__(self, other):
        return other % self.value

    def __mul__(self, other):
        return self.value * other

    def __rmul__(self, other):
        return other * self.value

    def __call__(self, *args, **kwargs):
        return self.value(*args, **kwargs)  # type: ignore

    def __lt__(self, other: "LazyProxy") -> bool:
        return self.value < other  # type: ignore

    def __le__(self, other):
        return self.value <= other  # type: ignore

    def __eq__(self, other):
        return self.value == other

    def __ne__(self, other):
        return self.value != other

    def __gt__(self, other: str) -> bool:
        return self.value > other  # type: ignore

    def __ge__(self, other):
        return self.value >= other

    def __delattr__(self, name):
        delattr(self.value, name)

    def __getattr__(self, name: str):
        if self._attribute_error is not None:
            raise self._attribute_error
        return getattr(self.value, name)

    def __setattr__(self, name, value):
        setattr(self.value, name, value)

    def __delitem__(self, key):
        del self.value[key]  # type: ignore

    def __getitem__(self, key):
        return self.value[key]  # type: ignore

    def __setitem__(self, key, value):
        self.value[key] = value  # type: ignore

    def __copy__(self) -> "LazyProxy":
        return LazyProxy(
            self._func,
            enable_cache=self._is_cache_enabled,
            *self._args,
            **self._kwargs
        )

    def __deepcopy__(self, memo: t.Dict[t.Any, t.Any]) -> "LazyProxy":
        from copy import deepcopy
        return LazyProxy(
            deepcopy(self._func, memo),
            enable_cache=deepcopy(self._is_cache_enabled, memo),
            *deepcopy(self._args, memo),
            **deepcopy(self._kwargs, memo)
        )


try:
    from typing import Protocol
except ImportError:
    from typing_extensions import Protocol  # type: ignore


class _TranslationsReader(Protocol):
    def read(self) -> bytes:
        ...

    # optional:
    # name: str


class NullTranslations(gettext.NullTranslations):

    DEFAULT_DOMAIN: t.Optional[str] = None

    # from `gettext.Nulltranslations`. not in gettext stub because private.
    # however, we always set the fallback to a `NullTranslations` instance
    # instead of a `gettext.NullTranslations` one,
    # so this declaration is necessary to inform about a stricter type.
    _fallback: "NullTranslations"
    _info: dict

    _domains: t.Dict[str, "Translations"]
    _catalog: t.Dict[t.Union[str, tuple[str, int]], str]
    domain: t.Optional[str]
    files: t.List[str]
    # mypy thinks this instance variable is a method if we declare it here
    # plural: t.Callable[[int], int]

    def __init__(self, fp: _TranslationsReader = None) -> None:
        """Initialize a simple translations class which is not backed by a
        real catalog. Behaves similar to gettext.NullTranslations but also
        offers Babel's on *gettext methods (e.g. 'dgettext()').

        :param fp: a file-like object (ignored in this class)
        """
        # These attributes are set by gettext.NullTranslations when a catalog
        # is parsed (fp != None). Ensure that they are always present because
        # some *gettext methods (including '.gettext()') rely on the attributes.
        self._catalog = {}
        self.plural: t.Callable[[int], int] = lambda n: int(n != 1)
        super().__init__(fp=fp)
        self.files = list(filter(None, [getattr(fp, 'name', None)]))
        self.domain = self.DEFAULT_DOMAIN
        self._domains = {}

    def dgettext(self, domain: str, message: str) -> str:
        """Like ``gettext()``, but look the message up in the specified
        domain.
        """
        return self._domains.get(domain, self).gettext(message)

    def ldgettext(self, domain: str, message: str) -> str:
        """Like ``lgettext()``, but look the message up in the specified
        domain.
        """
        import warnings
        warnings.warn('ldgettext() is deprecated, use dgettext() instead',
                      DeprecationWarning, 2)
        return self._domains.get(domain, self).lgettext(message)

    def udgettext(self, domain: str, message: str) -> str:
        """Like ``ugettext()``, but look the message up in the specified
        domain.
        """
        return self._domains.get(domain, self).ugettext(message)
    # backward compatibility with 0.9
    dugettext = udgettext

    def dngettext(self, domain: str, singular: str, plural: str, num: int) -> str:
        """Like ``ngettext()``, but look the message up in the specified
        domain.
        """
        return self._domains.get(domain, self).ngettext(singular, plural, num)

    def ldngettext(self, domain: str, singular: str, plural: str, num: int) -> str:
        """Like ``lngettext()``, but look the message up in the specified
        domain.
        """
        import warnings
        warnings.warn('ldngettext() is deprecated, use dngettext() instead',
                      DeprecationWarning, 2)
        return self._domains.get(domain, self).lngettext(singular, plural, num)

    def udngettext(self, domain: str, singular: str, plural: str, num: int) -> str:
        """Like ``ungettext()`` but look the message up in the specified
        domain.
        """
        return self._domains.get(domain, self).ungettext(singular, plural, num)
    # backward compatibility with 0.9
    dungettext = udngettext

    # Most of the downwards code, until it get's included in stdlib, from:
    #    https://bugs.python.org/file10036/gettext-pgettext.patch
    #
    # The encoding of a msgctxt and a msgid in a .mo file is
    # msgctxt + "\x04" + msgid (gettext version >= 0.15)
    CONTEXT_ENCODING = '%s\x04%s'

    def pgettext(self, context: str, message: str) -> str:
        """Look up the `context` and `message` id in the catalog and return the
        corresponding message string, as an 8-bit string encoded with the
        catalog's charset encoding, if known.  If there is no entry in the
        catalog for the `message` id and `context` , and a fallback has been
        set, the look up is forwarded to the fallback's ``pgettext()``
        method. Otherwise, the `message` id is returned.
        """
        ctxt_msg_id = self.CONTEXT_ENCODING % (context, message)
        missing = object()
        tmsg = self._catalog.get(ctxt_msg_id, missing)
        if tmsg is missing:
            if self._fallback:
                return self._fallback.pgettext(context, message)
            return message
        return t.cast(str, tmsg)

    def lpgettext(self, context, message: str) -> bytes:
        """Equivalent to ``pgettext()``, but the translation is returned in the
        preferred system encoding, if no other encoding was explicitly set with
        ``bind_textdomain_codeset()``.
        """
        import warnings
        warnings.warn('lpgettext() is deprecated, use pgettext() instead',
                      DeprecationWarning, 2)
        tmsg = self.pgettext(context, message)
        encoding = getattr(self, "_output_charset", None) or locale.getpreferredencoding()
        return tmsg.encode(encoding)

    def npgettext(self, context: str, singular: str, plural: str, num: int) -> str:
        """Do a plural-forms lookup of a message id.  `singular` is used as the
        message id for purposes of lookup in the catalog, while `num` is used to
        determine which plural form to use.  The returned message string is an
        8-bit string encoded with the catalog's charset encoding, if known.

        If the message id for `context` is not found in the catalog, and a
        fallback is specified, the request is forwarded to the fallback's
        ``npgettext()`` method.  Otherwise, when ``num`` is 1 ``singular`` is
        returned, and ``plural`` is returned in all other cases.
        """
        ctxt_msg_id = self.CONTEXT_ENCODING % (context, singular)
        try:
            tmsg = self._catalog[(ctxt_msg_id, self.plural(num))]
            return tmsg
        except KeyError:
            if self._fallback:
                return self._fallback.npgettext(context, singular, plural, num)
            if num == 1:
                return singular
            else:
                return plural

    def lnpgettext(self, context, singular: str, plural: str, num: int) -> t.Union[str, bytes]:
        """Equivalent to ``npgettext()``, but the translation is returned in the
        preferred system encoding, if no other encoding was explicitly set with
        ``bind_textdomain_codeset()``.
        """
        import warnings
        warnings.warn('lnpgettext() is deprecated, use npgettext() instead',
                      DeprecationWarning, 2)
        ctxt_msg_id = self.CONTEXT_ENCODING % (context, singular)
        try:
            tmsg = self._catalog[(ctxt_msg_id, self.plural(num))]
            encoding = getattr(self, "_output_charset", None) or locale.getpreferredencoding()
            return tmsg.encode(encoding)
        except KeyError:
            if self._fallback:
                return self._fallback.lnpgettext(context, singular, plural, num)
            if num == 1:
                return singular
            else:
                return plural

    def upgettext(self, context: str, message: str) -> str:
        """Look up the `context` and `message` id in the catalog and return the
        corresponding message string, as a Unicode string.  If there is no entry
        in the catalog for the `message` id and `context`, and a fallback has
        been set, the look up is forwarded to the fallback's ``upgettext()``
        method.  Otherwise, the `message` id is returned.
        """
        ctxt_message_id = self.CONTEXT_ENCODING % (context, message)
        missing = object()
        tmsg = self._catalog.get(ctxt_message_id, missing)
        if tmsg is missing:
            if self._fallback:
                return self._fallback.upgettext(context, message)
            return str(message)
        return t.cast(str, tmsg)

    def unpgettext(self, context: str, singular: str, plural: str, num: int) -> str:
        """Do a plural-forms lookup of a message id.  `singular` is used as the
        message id for purposes of lookup in the catalog, while `num` is used to
        determine which plural form to use.  The returned message string is a
        Unicode string.

        If the message id for `context` is not found in the catalog, and a
        fallback is specified, the request is forwarded to the fallback's
        ``unpgettext()`` method.  Otherwise, when `num` is 1 `singular` is
        returned, and `plural` is returned in all other cases.
        """
        ctxt_message_id = self.CONTEXT_ENCODING % (context, singular)
        try:
            tmsg = self._catalog[(ctxt_message_id, self.plural(num))]
        except KeyError:
            if self._fallback:
                return self._fallback.unpgettext(context, singular, plural, num)
            if num == 1:
                tmsg = str(singular)
            else:
                tmsg = str(plural)
        return tmsg

    def dpgettext(self, domain: str, context: str, message: str) -> str:
        """Like `pgettext()`, but look the message up in the specified
        `domain`.
        """
        return self._domains.get(domain, self).pgettext(context, message)

    def udpgettext(self, domain: str, context: str, message: str) -> str:
        """Like `upgettext()`, but look the message up in the specified
        `domain`.
        """
        return self._domains.get(domain, self).upgettext(context, message)
    # backward compatibility with 0.9
    dupgettext = udpgettext

    def ldpgettext(self, domain: str, context, message: str) -> bytes:
        """Equivalent to ``dpgettext()``, but the translation is returned in the
        preferred system encoding, if no other encoding was explicitly set with
        ``bind_textdomain_codeset()``.
        """
        return self._domains.get(domain, self).lpgettext(context, message)

    def dnpgettext(
        self, domain: str, context: str, singular: str, plural: str, num: int
    ) -> str:
        """Like ``npgettext``, but look the message up in the specified
        `domain`.
        """
        return self._domains.get(domain, self).npgettext(context, singular,
                                                         plural, num)

    def udnpgettext(
        self, domain: str, context: str, singular: str, plural: str, num: int
    ) -> str:
        """Like ``unpgettext``, but look the message up in the specified
        `domain`.
        """
        return self._domains.get(domain, self).unpgettext(context, singular,
                                                          plural, num)
    # backward compatibility with 0.9
    dunpgettext = udnpgettext

    def ldnpgettext(
        self, domain: str, context, singular: str, plural: str, num: int
    ) -> t.Union[str, bytes]:
        """Equivalent to ``dnpgettext()``, but the translation is returned in
        the preferred system encoding, if no other encoding was explicitly set
        with ``bind_textdomain_codeset()``.
        """
        return self._domains.get(domain, self).lnpgettext(context, singular,
                                                          plural, num)

    ugettext = gettext.NullTranslations.gettext
    ungettext = gettext.NullTranslations.ngettext


try:
    LocaleLike: t.TypeAlias = t.Union[Locale, str]
except AttributeError:
    LocaleLike = t.Union[Locale, str]  # type: ignore



class Translations(NullTranslations, gettext.GNUTranslations):
    """An extended translation catalog class."""

    DEFAULT_DOMAIN = 'messages'

    def __init__(
        self,
        fp: _TranslationsReader = None,
        domain: t.Optional[str] = None,
    ) -> None:
        """Initialize the translations catalog.

        :param fp: the file-like object the translation should be read from
        :param domain: the message domain (default: 'messages')
        """
        super().__init__(fp=fp)
        self.domain = domain or self.DEFAULT_DOMAIN

    ugettext = gettext.GNUTranslations.gettext
    ungettext = gettext.GNUTranslations.ngettext

    @classmethod
    def load(
        cls,
        dirname: t.Optional[str] = None,
        locales: t.Optional[t.Union[t.Tuple[LocaleLike], t.List[LocaleLike], LocaleLike]] = None,
        domain: t.Optional[str] = None,
    ) -> NullTranslations:
        """Load translations from the given directory.

        :param dirname: the directory containing the ``MO`` files
        :param locales: the list of locales in order of preference (items in
                        this list can be either `Locale` objects or locale
                        strings)
        :param domain: the message domain (default: 'messages')
        """
        if locales is not None:
            if not isinstance(locales, (list, tuple)):
                locales = [locales]  # type: ignore
            locales = [str(locale) for locale in locales]  # type: ignore
        # mypy is not too good at inferring tpyes in branches correctly
        # when redefinitions are at play, so we make a forceful assertion
        locales = t.cast(t.Optional[t.List[str]], locales)

        if not domain:
            domain = cls.DEFAULT_DOMAIN
        filename = gettext.find(domain, dirname, locales)
        if not filename:
            return NullTranslations()
        with open(filename, 'rb') as fp:
            return cls(fp=fp, domain=domain)

    def __repr__(self):
        return '<%s: "%s">' % (type(self).__name__,
                               self._info.get('project-id-version'))

    def add(self, translations: "Translations", merge: bool = True) -> "Translations":
        """Add the given translations to the catalog.

        If the domain of the translations is different than that of the
        current catalog, they are added as a catalog that is only accessible
        by the various ``d*gettext`` functions.

        :param translations: the `Translations` instance with the messages to
                             add
        :param merge: whether translations for message domains that have
                      already been added should be merged with the existing
                      translations
        """
        domain = getattr(translations, 'domain', self.DEFAULT_DOMAIN)
        if merge and domain == self.domain:
            return self.merge(translations)

        existing = self._domains.get(domain)
        if merge and existing is not None:
            existing.merge(translations)
        else:
            translations.add_fallback(self)
            self._domains[domain] = translations

        return self

    def merge(self, translations: "Translations") -> "Translations":
        """Merge the given translations into the catalog.

        Message translations in the specified catalog override any messages
        with the same identifier in the existing catalog.

        :param translations: the `Translations` instance with the messages to
                             merge
        """
        if isinstance(translations, gettext.GNUTranslations):
            self._catalog.update(translations._catalog)
            if isinstance(translations, Translations):
                self.files.extend(translations.files)

        return self
