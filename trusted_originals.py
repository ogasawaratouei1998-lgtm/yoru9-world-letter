"""Editorially vetted news publishers whose reporting is accepted on trust.

Only a valid article URL on this allowlist is required as news provenance;
fact investigation and corroboration remain the reporting company's job.
"""
from urllib.parse import urlsplit

TRUSTED_ORIGINAL_PUBLISHERS = (
    "bbc.com", "bbc.co.uk", "theguardian.com", "guardian.co.uk",
    "npr.org", "cbsnews.com", "nbcnews.com", "nytimes.com",
    "abc.net.au", "cbc.ca", "france24.com", "lemonde.fr",
    "dw.com", "elpais.com", "japantimes.co.jp", "thehindu.com",
    "globo.com", "premiumtimesng.com", "inquirer.net",
    "reuters.com", "apnews.com", "nhk.or.jp", "kyodonews.net",
    "upi.com", "koreaherald.com", "straitstimes.com",
    "africanews.com", "aljazeera.com", "rte.ie", "euronews.com",
    "independent.co.uk", "skynews.com", "spiegel.de",
    "scmp.com", "timesofindia.indiatimes.com", "ndtv.com",
    "theverge.com", "techcrunch.com", "wired.com", "latimes.com",
    # Original game-show episode coverage with identifiable reporter and airing date.
    "tvinsider.com",
    "pbs.org", "axios.com", "time.com", "foxnews.com",
    "abcnews.go.com", "nypost.com", "phys.org",
    "mashable.com", "quantamagazine.org", "newscientist.com",
    "propublica.org", "theatlantic.com", "newyorker.com",
    "vox.com", "skysports.com", "espn.com", "formula1.com",
    "arstechnica.com", "gizmodo.com", "engadget.com",
    "scientificamerican.com", "rnz.co.nz",
    # News publishers from underrepresented markets; no additional reporting
    # verification is imposed by our app.
    "punchng.com", "vanguardngr.com", "guardian.ng",
    "standardmedia.co.ke", "dailymaverick.co.za",
    "myjoyonline.com", "egyptindependent.com", "hespress.com",
    "independent.co.ug", "dailynews.co.tz", "nyasatimes.com",
    "antaranews.com", "vnexpress.net", "dawn.com",
    "thedailystar.net", "timesofisrael.com", "arabnews.com",
    "dailysabah.com", "fbcnews.com.fj", "postcourier.com.pg",
    "sbs.com.au", "ansa.it", "repubblica.it",
    "notesfrompoland.com", "eldiario.es", "20minutos.es",
    "observador.pt", "clarin.com", "rpp.pe",
    "abc.com.py", "prensalibre.com", "eluniverso.com",
    "elobservador.com.uy",
)

SINGLE_SOURCE_NOTE = ("報道機関1社の独自取材記事を確認しています。"
                      "別媒体による独立した裏付けは確認できていません。")


def trusted_original_domain(url):
    if not isinstance(url,str):
        return False
    try:
        parts=urlsplit(url)
        if (parts.scheme!="https" or not parts.hostname or
                parts.username or parts.password or
                parts.port not in (None,443)):
            return False
        hostname=parts.hostname.lower().removeprefix("www.")
    except ValueError:
        return False
    return any(hostname==domain or hostname.endswith("."+domain)
               for domain in TRUSTED_ORIGINAL_PUBLISHERS)
