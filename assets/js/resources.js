// Resources collection behaviour: category tabs, tag chips, search and
// the video player dialog. Everything is progressive - the page renders
// complete without this script; the script only filters what is already
// there and swaps the poster facade for a playing player on request.
// Local files play in <video>. A YouTube id loads www.youtube-nocookie.com
// only after the reader presses play (disclosed on the privacy page).
// Built HTML never includes a YouTube URL.
(function () {
  "use strict";

  var grid = document.querySelector("[data-collection-grid]");
  var dialog = document.querySelector("[data-video-dialog]");

  // Player dialog: one shared <dialog> for every card on the page.
  if (dialog) {
    var dlgVideo = dialog.querySelector("video");
    var dlgYoutube = dialog.querySelector("[data-dialog-youtube]");
    var dlgTitle = dialog.querySelector("[data-dialog-title]");
    var clearYoutube = function () {
      if (!dlgYoutube) return;
      dlgYoutube.innerHTML = "";
      dlgYoutube.hidden = true;
    };
    var openPlayer = function (btn) {
      var yt = btn.getAttribute("data-youtube-id") || "";
      dlgTitle.textContent = btn.getAttribute("data-title") || "";
      if (yt) {
        dlgVideo.pause();
        dlgVideo.removeAttribute("src");
        dlgVideo.innerHTML = "";
        dlgVideo.load();
        dlgVideo.hidden = true;
        if (dlgYoutube) {
          dlgYoutube.hidden = false;
          dlgYoutube.innerHTML = "";
          var iframe = document.createElement("iframe");
          iframe.src = "https://www.youtube-nocookie.com/embed/" + encodeURIComponent(yt) + "?rel=0&autoplay=1";
          iframe.setAttribute("allow", "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture");
          iframe.setAttribute("allowfullscreen", "");
          iframe.setAttribute("title", btn.getAttribute("data-title") || "Video");
          iframe.setAttribute("width", "960");
          iframe.setAttribute("height", "540");
          dlgYoutube.appendChild(iframe);
        }
      } else {
        clearYoutube();
        dlgVideo.hidden = false;
        dlgVideo.innerHTML = "";
        var sources = JSON.parse(btn.getAttribute("data-sources") || "[]");
        sources.forEach(function (s) {
          var el = document.createElement("source");
          el.src = s.src;
          el.type = s.type;
          dlgVideo.appendChild(el);
        });
        var poster = btn.getAttribute("data-poster");
        if (poster) dlgVideo.setAttribute("poster", poster);
        else dlgVideo.removeAttribute("poster");
        dlgVideo.load();
      }
      if (typeof dialog.showModal === "function") dialog.showModal();
      if (!yt) dlgVideo.play().catch(function () {});
    };
    document.querySelectorAll("[data-play-video]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        openPlayer(btn);
      });
    });
    dialog.querySelector("[data-dialog-close]").addEventListener("click", function () {
      dialog.close();
    });
    dialog.addEventListener("close", function () {
      dlgVideo.pause();
      dlgVideo.removeAttribute("src");
      dlgVideo.innerHTML = "";
      dlgVideo.hidden = false;
      dlgVideo.load();
      clearYoutube();
    });
  }

  if (!grid) return;

  var cards = Array.prototype.slice.call(grid.querySelectorAll("[data-card]"));
  var tabs = Array.prototype.slice.call(document.querySelectorAll("[data-category-tab]"));
  var chips = Array.prototype.slice.call(document.querySelectorAll("[data-tag-chip]"));
  var search = document.querySelector("[data-collection-search]");
  var status = document.querySelector("[data-collection-status]");
  var activeCategory = "all";
  var activeTags = {};
  var query = "";

  var apply = function () {
    var shown = 0;
    cards.forEach(function (card) {
      var inCategory = activeCategory === "all" || card.getAttribute("data-category") === activeCategory;
      var cardTags = (card.getAttribute("data-tags") || "").split(" ");
      var inTags = Object.keys(activeTags).every(function (t) {
        return cardTags.indexOf(t) !== -1;
      });
      var inQuery = !query || (card.getAttribute("data-search") || "").indexOf(query) !== -1;
      var visible = inCategory && inTags && inQuery;
      card.hidden = !visible;
      if (visible) shown += 1;
    });
    // Hidden cards leave gaps in the deal; hand it out again to the visible ones (card-deal.js).
    window.blowhornCardDeal(grid);
    if (status) {
      status.textContent = shown === cards.length ? "" : shown + " of " + cards.length + " " + (grid.getAttribute("data-collection-noun") || "items") + " shown";
    }
  };

  tabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      activeCategory = tab.getAttribute("data-category-tab");
      tabs.forEach(function (t) {
        t.setAttribute("aria-pressed", t === tab ? "true" : "false");
      });
      apply();
      if (history.replaceState) {
        history.replaceState(null, "", activeCategory === "all" ? location.pathname : "#" + activeCategory);
      }
    });
  });

  chips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      var tag = chip.getAttribute("data-tag-chip");
      if (activeTags[tag]) {
        delete activeTags[tag];
        chip.setAttribute("aria-pressed", "false");
      } else {
        activeTags[tag] = true;
        chip.setAttribute("aria-pressed", "true");
      }
      apply();
    });
  });

  if (search) {
    search.addEventListener("input", function () {
      query = search.value.trim().toLowerCase();
      apply();
    });
  }

  // Deep link: #<category> preselects the tab, like the Layer5 docs
  // videos landing this section is modelled on.
  if (location.hash.length > 1) {
    var wanted = location.hash.slice(1);
    tabs.forEach(function (tab) {
      if (tab.getAttribute("data-category-tab") === wanted) tab.click();
    });
  }

  apply();
})();
