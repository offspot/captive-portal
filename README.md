# portal-app

A python web-app to support the UI of our home-portal image.

[![CodeFactor](https://www.codefactor.io/repository/github/offspot/home-portal-app/badge)](https://www.codefactor.io/repository/github/offspot/home-portal-app)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

This is an adaptation of [IIAB](https://internet-in-a-box.org/)'s [captive-portal feature](https://github.com/iiab/iiab/blob/master/roles/captiveportal/README.md) for [Kiwix](https://kiwix.org) Hotspot.

It's goal is to support Kiwix Hotspot's *home-portal* feature: trigger a UI on WiFi connection to the hotspot to inform about the URL of the main content. To do so, it mimicks a [captive portal](https://en.wikipedia.org/wiki/Captive_portal).

Because of how captive portal works, it is very dependent on how this is deployed and how the users are redirected to this app.
Our deployment is dcocumented at [container-images/home-portal](https://github.com/offspot/container-images/tree/main/home-portal).

## reusing

You are invited to reuse this app on your portal project, mostly because it holds important logic of how various systems attempts to detect captive-portals and how such ones should react.

## behavior

- An (separate, see *Filter Module* below) captive-portal mechanism redirects HTTP requests (intended for system-specific server) to this app.
- this app receives the request and returns a web page informing the User about the final URL it should access, asking him to confirm.
- this response is usually displayed in an ad-hoc popup/window upon WiFi connection and allow closing/close-itself upon certain condition.
- the app records (in an SQLite DB) that it has seen this User using it's MAC address and IP address.
- upon *confirmation* by User, it *registers* him by setting a registration date on the record and request the *filter module* to allow traffic.
- User's system detects that it it no longer *blocked* and finishes the popup session.

## compatibility

Version `1.0.0` has been tested with the following platforms

| Platform               | Status        | Comment             |
| ---------------------- | ------------- | ------------------- |
| macOS 11 Big Sur       | ✅            |                     |
| macOS 12 Monterey      | ✅            |                     |
| macOS 13 Ventura       | ✅            |                     |
| iOS 16.1               | ✅            |                     |
| Ubuntu 22.10           | ✅ (no popup) |                     |
| Fedora 37              | ✅ (no popup) |                     |
| Firefox 106            | ✅            |                     |
| Android 13             | ✅            |                     |
| Windows 10 20H2        | ✅            |                     |
| Windows 11 21H2        | ✅            |                     |

Should you encounter a system for which it doesn't work, please [Open a ticket](https://github.com/offspot/home-portal-app/issues/new/choose) specifying the System and its Version.

## Configuration

Configuration is done solely via environment variables

| Variable            | Default               | Usage                                                             |
| ------------------- | --------------------- | ----------------------------------------------------------------- |
| `HOTSPOT_NAME`      | `default`             | Name of the hotspot, displayed on portal and as title             |
| `HOTSPOT_FQDN`      | `default.hotspot`     | URL (hostname actualy) to point users to.                         |
| `TIMEOUT`           | `60`                  | Minutes after which to consider an *inactive* client unregistered |
| `FOOTER_NOTE`       |                       | Small text displayed on footer of portal                          |
| `DEBUG`             |                       | Set any value to trigger debug logging                            |
| `DB_PATH`           | `portal-users.db`     | Path to store the SQLite DB to                                    |
| `FILTER_MODULE`     | `dummy_portal_filter` | Name of python module to use as *filter*. `portal_filter` is ours |
| `DONT_SETUP_FILTER` |                       | Set any value to skip *filter module* setup on start              |
| `BIND_TO`           | `127.0.0.1`           | IP to bind to when using entrypoint directly (not via uwsgi)      |
| `PORT`              | `3000`                | Port to bind to when using entrypoint directly (not via uwsgi)    |

### Notes

- **Inactive** clients are devices that stopped making network connections. On modern systems, this usually not happens as most OS phone home frequently (including for captive portal detection!). This is thus mostly used to detect *disconnected* or *sleeping* devices.
- We do this because we assume devices can be shared by multiple users who might not know our main content URL.
- App is somewhat flexible regarding the *filter module*. we only use and tested the `portal_filter` one but the default (dummy) one is much useful during portal-UI development.

## [dev] i18n updates

``` sh
# update message catalog
pybabel extract -F portal/babel.cfg -o portal/locale/messages.pot portal/
# add new locale (once per locale)
pybabel init -i portal/locale/messages.pot -d portal/locale -l fr
# update locales
pybabel update -i portal/locale/messages.pot -d portal/locale
# compile locales
pybabel compile -d portal/locale
```

# Filter module

For the portal-app to work, it needs to be called by OS upon WiFi connection. This is know as *captive-portal*.

There are many ways to implement a captive-portal and because it is not standardized, each OS or platform implements its own mechanism. All of them share some common properties though:

- Upon connection status change as well as frequently (periodically), the *platform* contacts a known web server over HTTP, expecting a predefined answer.
- Should the answer be the expected one, *platform* considers it not being on a captive-portal. Note that this is different from considering the connection *Online* or *Limited*.
- If the answer is different, *platform* considers itself on a captive-portal and will display a popup/window with that *test page*, expecting the captive-portal UI to show up, until that same requests eventually replies correctly.

Most captive-portal have for goal to prevent all internet access until the captive-portal UI is used to make a kind of authentication or payment. This is **not our case**. We **just want to trigger the UI** to inform about our main URL. This means that our implementation is much more relaxed and can be abused easily. Don't use it for an actual captive-portal!

To trigger the UI, we redirect all HTTP/s requests to our IP on port `2080`/`2443` within a defined network until the client's IP is added to a special chain.

## behavior

- http/s packets from captured networks and not for hotspot are sent to `CAPTIVE_HTTP` and `CAPTIVE_HTTPS` chains
- if source ip is in `CAPTIVE_PASSLIST` chain, it is accepted
- if not, its redirected to `hotspot_ip:2080` or `hotspot_ip:2443`

Portal UI calls back once its user is *registered* and we add its IP to `CAPTIVE_PASSLIST`

A periodic clean-up of passlist is expected as device-clients are expected to be used by various users over time.

**Sample netfilter configuration**

```
$ sudo nft -a list table nat
table ip nat { # handle 1
    chain PREROUTING { # handle 2
        ip saddr 192.168.2.128/25 tcp dport 80 counter packets 648 bytes 41448 jump CAPTIVE_HTTP comment "Captured HTTP traffic to CAPTIVE_HTTP" # handle 6
        ip saddr 192.168.2.128/25 tcp dport 443 counter packets 9819 bytes 624438 jump CAPTIVE_HTTPS comment "Captured HTTPS traffic to CAPTIVE_HTTPS" # handle 7
    }

    chain CAPTIVE_HTTP { # handle 3
        ip protocol tcp counter packets 648 bytes 41448 jump CAPTIVE_PASSLIST comment "Jump to CAPTIVE_PASSLIST to try to escape filtering" # handle 8
        ip protocol tcp counter packets 542 bytes 34996 dnat to 192.168.2.1:2080 comment "redirect HTTP(s) traffic to hotspot server port 2080" # handle 9
    }

    chain CAPTIVE_HTTPS { # handle 4
        ip protocol tcp counter packets 9819 bytes 624438 jump CAPTIVE_PASSLIST comment "Jump to CAPTIVE_PASSLIST to try to escape filtering" # handle 10
        ip protocol tcp counter packets 9409 bytes 599198 dnat to 192.168.2.1:2443 comment "redirect HTTP(s) traffic to hotspot server port 2443" # handle 11
    }

    chain CAPTIVE_PASSLIST { # handle 5
        ip saddr 192.168.2.174 counter packets 3 bytes 192 accept comment "allow host" # handle 13
        ip protocol tcp counter packets 9951 bytes 634194 return comment "return non-accepted to calling chain (captive_httpx)" # handle 12
    }
}
```


## Configuration

Configuration is done solely via environment variables

| Variable             | Default       | Usage                                                                       |
| -------------------- | ------------- | --------------------------------------------------------------------------- |
| `HOSTPOT_IP`         | `192.168.2.1` | IP to redirect unregistered HTTP traffic to                                 |
| `CAPTURED_NETWORKS`  |               | List of `|` separated networks to limit *capture* to. Otherwise any traffic |
| `HTTP_PORT`          | `2080`        | Port to redirect captured HTTP traffic to on *HOTSPOT_IP*                   |
| `HTTPS_PORT`         | `2443`        | Port to redirect captured HTTPS traffic to on *HOTSPOT_IP*                  |
