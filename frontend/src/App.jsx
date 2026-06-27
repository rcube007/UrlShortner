import { useEffect, useState } from 'react';

const HISTORY_KEY = 'shortener-history';
const MAX_HISTORY = 10;

function App() {
  const [longUrl, setLongUrl] = useState('');
  const [shortUrl, setShortUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [history, setHistory] = useState([]);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const savedHistory = window.localStorage.getItem(HISTORY_KEY);
    if (savedHistory) {
      try {
        setHistory(JSON.parse(savedHistory));
      } catch {
        window.localStorage.removeItem(HISTORY_KEY);
      }
    }
  }, []);

  const saveHistory = (nextItem) => {
    setHistory((prev) => {
      const updated = [nextItem, ...prev].slice(0, MAX_HISTORY);
      window.localStorage.setItem(HISTORY_KEY, JSON.stringify(updated));
      return updated;
    });
  };

  const copyToClipboard = async () => {
    if (!shortUrl) return;
    try {
      await navigator.clipboard.writeText(shortUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setError('Unable to copy to clipboard');
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError('');
    setShortUrl('');
    setCopied(false);

    try {
      const response = await fetch(`/shorten?long_url=${encodeURIComponent(longUrl)}`, {
        method: 'POST',
        headers: {
          'Idempotency-Key': crypto.randomUUID(),
        },
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Unable to shorten URL');
      }

      const generatedShortUrl = data.short_url || '';
      setShortUrl(generatedShortUrl);
      if (generatedShortUrl) {
        saveHistory({ longUrl, shortUrl: generatedShortUrl });
      }
    } catch (err) {
      setError(err.message || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <div className="card">
        <h1>URL Shortener</h1>
        <p>Paste a long URL and get a short one instantly.</p>

        <form onSubmit={handleSubmit}>
          <input
            type="url"
            value={longUrl}
            onChange={(event) => setLongUrl(event.target.value)}
            placeholder="https://example.com"
            required
          />
          <button type="submit" disabled={loading}>
            {loading ? 'Shortening...' : 'Shorten URL'}
          </button>
        </form>

        <div className="output" aria-live="polite">
          {error ? (
            <p className="error">{error}</p>
          ) : shortUrl ? (
            <>
              <label>Short URL</label>
              <div className="short-url-row">
                <a href={shortUrl} target="_blank" rel="noreferrer">
                  {shortUrl}
                </a>
                <button type="button" className="copy-button" onClick={copyToClipboard}>
                  {copied ? 'Copied!' : 'Copy'}
                </button>
              </div>
            </>
          ) : (
            <p>Your shortened URL will appear here.</p>
          )}
        </div>

        <div className="history-card">
          <h2>Recent URLs</h2>
          {history.length === 0 ? (
            <p>No recent links yet.</p>
          ) : (
            <ul>
              {history.map((item, index) => (
                <li key={`${item.shortUrl}-${index}`}>
                  <div className="history-link">
                    <a href={item.shortUrl} target="_blank" rel="noreferrer">
                      {item.shortUrl}
                    </a>
                    <span>{item.longUrl}</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
