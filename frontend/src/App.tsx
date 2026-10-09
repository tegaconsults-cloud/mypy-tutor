import React, { Suspense, useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';
import { globalStyles } from '@/styles/shared';

// Lazy-load page components — build passes even before these files exist
// because React.lazy defers the import to runtime, not build time.
const PaymentPage = React.lazy(() => import('@/pages/PaymentPage'));
const CertificateLockedPage = React.lazy(
  () => import('@/pages/CertificateLockedPage')
);
const CertificateNotFoundPage = React.lazy(
  () => import('@/pages/CertificateNotFoundPage')
);
const CertificateVerifiedPage = React.lazy(
  () => import('@/pages/CertificateVerifiedPage')
);
const TermsPage = React.lazy(() => import('@/pages/TermsPage'));
const PrivacyPage = React.lazy(() => import('@/pages/PrivacyPage'));
const VoiceGuidePage = React.lazy(() => import('@/pages/VoiceGuidePage'));

/** Full-screen centered loading indicator shown while a lazy chunk loads */
function PageLoader() {
  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#07090f',
        color: '#94a3b8',
        fontSize: '1rem',
        fontFamily: "'Segoe UI', Arial, sans-serif",
      }}
    >
      Loading…
    </div>
  );
}

/** Placeholder rendered for the catch-all / route before other pages exist */
function PlaceholderHome() {
  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#07090f',
        color: '#e2e8f0',
        fontFamily: "'Segoe UI', Arial, sans-serif",
      }}
    >
      <p>MyPy Tutor</p>
    </div>
  );
}

export default function App() {
  // Inject global body styles once on mount
  useEffect(() => {
    const styleId = 'mpt-global-styles';
    if (!document.getElementById(styleId)) {
      const tag = document.createElement('style');
      tag.id = styleId;
      tag.textContent = globalStyles;
      document.head.appendChild(tag);
    }
  }, []);

  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route path="/payment" element={<PaymentPage />} />
        <Route
          path="/certificate/locked"
          element={<CertificateLockedPage />}
        />
        <Route
          path="/certificate/not-found"
          element={<CertificateNotFoundPage />}
        />
        <Route
          path="/verify/:certId"
          element={<CertificateVerifiedPage />}
        />
        <Route path="/terms"   element={<TermsPage />} />
        <Route path="/privacy" element={<PrivacyPage />} />
        <Route path="/voice"   element={<VoiceGuidePage />} />
        {/* Catch-all — replaced once a real home/dashboard component exists */}
        <Route path="*" element={<PlaceholderHome />} />
      </Routes>
    </Suspense>
  );
}
