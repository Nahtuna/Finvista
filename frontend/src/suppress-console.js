if (typeof window !== "undefined") {
  // Suppress React DevTools install recommendation
  window.__REACT_DEVTOOLS_GLOBAL_HOOK__ = window.__REACT_DEVTOOLS_GLOBAL_HOOK__ || {
    supportsFiber: true,
    inject: () => {},
    onCommitFiberRoot: () => {},
    onCommitFiberUnmount: () => {}
  };

  // Suppress extension-related or liveness warning pollution
  const ignorePatterns = [
    "ObjectMultiplex",
    "MaxListenersExceededWarning",
    "app-init-liveness",
    "background-liveness"
  ];

  const wrapConsole = (method) => {
    const original = console[method];
    if (original) {
      console[method] = function (...args) {
        const text = args.map(x => String(x)).join(" ");
        if (ignorePatterns.some(pat => text.includes(pat))) return;
        original.apply(console, args);
      };
    }
  };

  wrapConsole("warn");
  wrapConsole("log");
  wrapConsole("error");
}
