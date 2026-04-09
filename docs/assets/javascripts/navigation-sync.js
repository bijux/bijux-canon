function bijuxNormalizePath(target) {
  const url = new URL(target, window.location.href);
  const path = url.pathname.replace(/\/+$/, "");
  return path || "/";
}

function bijuxActiveSitePath() {
  const activeLink = document.querySelector(
    ".bijux-site-tabs .bijux-tabs__item--active [data-bijux-site-target]"
  );
  if (activeLink) {
    return bijuxNormalizePath(activeLink.getAttribute("data-bijux-site-target"));
  }

  const currentPath = bijuxNormalizePath(window.location.pathname);
  const siteLinks = document.querySelectorAll(
    ".bijux-site-tabs [data-bijux-site-target]"
  );
  let bestMatch = null;

  for (const link of siteLinks) {
    const linkPath = bijuxNormalizePath(
      link.getAttribute("data-bijux-site-target") || "/"
    );
    if (
      currentPath === linkPath ||
      (linkPath !== "/" && currentPath.startsWith(`${linkPath}/`))
    ) {
      if (!bestMatch || linkPath.length > bestMatch.length) {
        bestMatch = linkPath;
      }
    }
  }

  return bestMatch;
}

function bijuxSyncDetailStripVisibility() {
  const activeSitePath = bijuxActiveSitePath();
  const strips = document.querySelectorAll("[data-bijux-detail-strip]");

  for (const strip of strips) {
    const rootPath = bijuxNormalizePath(
      strip.getAttribute("data-bijux-detail-root") || "/"
    );
    strip.hidden = rootPath !== activeSitePath;
  }
}

function bijuxSyncDetailStripActiveState() {
  const activeStrip = document.querySelector("[data-bijux-detail-strip]:not([hidden])");
  const currentPath = bijuxNormalizePath(window.location.pathname);

  if (!activeStrip) {
    return;
  }

  let activeLink = null;

  for (const link of activeStrip.querySelectorAll("[data-bijux-detail-target]")) {
    const linkPath = bijuxNormalizePath(
      link.getAttribute("data-bijux-detail-target") || "/"
    );
    const isMatch =
      currentPath === linkPath ||
      (linkPath !== "/" && currentPath.startsWith(`${linkPath}/`));

    if (isMatch && (!activeLink || linkPath.length > activeLink.path.length)) {
      activeLink = { path: linkPath, node: link };
    }
  }

  for (const item of activeStrip.querySelectorAll(".bijux-tabs__item")) {
    item.classList.remove("bijux-tabs__item--active");
  }

  if (activeLink) {
    activeLink.node.closest(".bijux-tabs__item")?.classList.add(
      "bijux-tabs__item--active"
    );
  }
}

function bijuxRevealActiveNavigationTarget() {
  const activeDetailLink = document.querySelector(
    "[data-bijux-detail-strip]:not([hidden]) .bijux-tabs__item--active a"
  );
  const activeSidebarLink = document.querySelector(
    ".md-sidebar--primary .md-nav__link--active"
  );

  activeDetailLink?.scrollIntoView({
    block: "nearest",
    inline: "center",
  });
  activeSidebarLink?.scrollIntoView({
    block: "nearest",
    inline: "nearest",
  });
}

document$.subscribe(() => {
  bijuxSyncDetailStripVisibility();
  bijuxSyncDetailStripActiveState();
  bijuxRevealActiveNavigationTarget();
});
