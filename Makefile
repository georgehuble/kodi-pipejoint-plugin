ADDON_NAME := $(shell grep '<addon id="' addon.xml |cut -d\" -f2)
VERSION := $(shell grep '  version=' addon.xml |cut -d\" -f2)
FILES = addon.xml LICENSE README.md resources default.py icon.png
# Release asset name. It is independent of the archive layout: inside the zip the
# single top-level folder stays the add-on id ($(ADDON_NAME)), which is what Kodi
# validates, while the downloaded file carries the project name and version.
ASSET_NAME = kodi-pipejoint-plugin_v$(VERSION)
ZIP_NAME = $(ASSET_NAME).zip
REPO_NAME = repo-plugins
REPO_PLUGINS ?= ../$(REPO_NAME)
RELEASE_BRANCH ?= omega

all: dist

# Build the installable archive under the name the release pipeline publishes.
# docs/ is deliberately absent from FILES, so documentation assets never enter
# the packaged add-on.
dist:
	rm -rf $(ADDON_NAME) $(ZIP_NAME)
	mkdir -p $(ADDON_NAME)
	cp -r $(FILES) $(ADDON_NAME)/
	zip -r $(ZIP_NAME) $(ADDON_NAME)/ \
		--exclude \*.pyc
	rm -r $(ADDON_NAME)

# Prepare a release locally: write VERSION into the manifest, record the change,
# create the annotated tag and push the branch together with the tag. VERSION is
# given on the command line and overrides the manifest-derived value, e.g.
# `make release VERSION=0.0.2`.
release:
	@test -n "$(VERSION)" || { echo "usage: make release VERSION=x.y.z"; exit 1; }
	sed -i -E 's|^([[:space:]]*)version="[^"]*"|\1version="$(VERSION)"|' addon.xml
	grep -q 'version="$(VERSION)"' addon.xml
	git add addon.xml
	git commit -m "release: v$(VERSION)"
	git tag -a v$(VERSION) -m "v$(VERSION)"
	git push --follow-tags

prepare_release:
	[ -d "$(REPO_PLUGINS)" ] || \
		git clone --depth 5 -b $(RELEASE_BRANCH) https://github.com/xbmc/$(REPO_NAME) "$(REPO_PLUGINS)"
	git -C $(REPO_PLUGINS) stash
	git -C $(REPO_PLUGINS) checkout $(RELEASE_BRANCH)
	rm -rf $(REPO_PLUGINS)/$(ADDON_NAME)
	mkdir $(REPO_PLUGINS)/$(ADDON_NAME)
	cp -r $(FILES) $(REPO_PLUGINS)/$(ADDON_NAME)/
# Remove files unwanted in repo edition
	$(RM) $(REPO_PLUGINS)/$(ADDON_NAME)/resources/language/Makefile
	$(RM) $(REPO_PLUGINS)/$(ADDON_NAME)/resources/fanart.svg

# Remove locally built archives regardless of the version in their name.
clean:
	rm -f *.zip
