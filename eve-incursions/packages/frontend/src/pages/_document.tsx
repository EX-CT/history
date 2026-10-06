import {Head, Html, Main, NextScript} from 'next/document';

export default function MyDocument() {
  return (
    <Html lang={'en'}>
      <Head>
        <link rel="manifest" href="/site.webmanifest" />
        <meta name="Description" content="Get the current all the current and past incursion spawns for EVE Online. With useful information you can't get anywhere else." />
        <meta name="theme-color" content="#0f1115"/>
        <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
      </Head>
      <body>
      <script dangerouslySetInnerHTML={{__html: `
        (() => {
          const setTheme = (newTheme) => {
            window.__theme = newTheme;
            document.documentElement.setAttribute('data-theme', newTheme);
          }
          let preferredTheme;
          try {
            preferredTheme = localStorage.getItem('theme');
          } catch (err) { }
          window.__setPreferredTheme = function(newTheme) {
            setTheme(newTheme);
            try {
              localStorage.setItem('theme', newTheme);
            } catch (err) {}
          }
          var darkQuery = window.matchMedia('(prefers-color-scheme: dark)');
          darkQuery.addEventListener('change', function(e) {
            if (!localStorage.getItem('theme')) {
              setTheme(e.matches ? 'dark' : 'light');
            }
          });
          setTheme(preferredTheme || (darkQuery.matches ? 'dark' : 'light'));
        })();
        `}} />
      <Main />
      <NextScript />
      </body>
    </Html>
  );
}
