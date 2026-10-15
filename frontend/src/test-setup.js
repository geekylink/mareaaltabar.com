// jsdom lacks matchMedia and scrollTo, which the hero/UI code touches.
if (!window.matchMedia) {
  window.matchMedia = () => ({
    matches: false,
    addEventListener() {},
    removeEventListener() {},
  });
}

window.scrollTo = () => {};