import '../styles/tokens.css';
import '../styles/globals.css';
import '../styles/tables.css';
import '../styles/footer.css';
import {AppProps} from 'next/app';
import {useEffect} from 'react';
import Head from 'next/head';
import {Nav} from '../components/layout/Nav';
import {RetirementNotice} from '../components/layout/RetirementNotice';

function MyApp({Component, pageProps}: AppProps) {
  useEffect(() => {
    if (!('serviceWorker' in navigator)) return;
    if (process.env.NODE_ENV === 'production') {
      navigator.serviceWorker.register('/sw.js').catch(() => {});
    } else {
      // A caching service worker against `next dev` serves stale/offline pages
      // and adds cold-boot latency to every navigation — make sure it's gone.
      navigator.serviceWorker.getRegistrations().then(regs => regs.forEach(r => r.unregister())).catch(() => {});
    }
  }, []);

  return (
    <>
      <Head>
        <title>EVE Incursions</title>
        <meta name="viewport" content="width=device-width, initial-scale=1"/>
      </Head>
      <div className="app">
        <Nav/>
        <main className="main">
          <div className="container">
            <RetirementNotice/>
            <Component {...pageProps} />
          </div>
        </main>
        <footer className="footer">
          <div className="container">
            <p>
              EVE Online, the EVE logo, EVE and all associated logos and designs are the intellectual property of CCP hf. All artwork, screenshots,
              characters, vehicles, storylines, world facts or other recognizable features of the intellectual property relating to these trademarks are
              likewise the intellectual property of CCP hf. EVE Online and the EVE logo are the registered trademarks of CCP hf. All rights are reserved
              worldwide. All other trademarks are the property of their respective owners. CCP hf. has granted permission to shadowlauch.de to use EVE Online
              and all associated logos and designs for promotional and information purposes on its website but does not endorse, and is not in any way
              affiliated with, incursions.shadowlauch.de. CCP is in no way responsible for the content on or functioning of this website, nor can it be liable
              for any damage arising from the use of this website.
            </p>
          </div>
        </footer>
      </div>
    </>
  );
}

export default MyApp;
