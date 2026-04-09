function bijuxNormalizePath(target) {
  const url = new URL(target, window.location.origin);
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

document$.subscribe(() => {
  bijuxSyncDetailStripVisibility();
});
