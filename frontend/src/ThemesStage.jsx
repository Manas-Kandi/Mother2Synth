import "./ThemesStage.css";

export default function ThemesStage({ themes = [], atoms = [] }) {
  // Create a lookup for fast access to atom content
  const atomMap = Object.fromEntries(atoms.map(a => [a.id, a]));

  return (
    <section className="themes-stage">
      <div className="themes-grid">
        {themes.map((theme, i) => (
          <div key={i} className="theme-column">
            <h3 className="theme-title">{theme.label}</h3>
            <div className="theme-atoms">
              {theme.atom_ids.map((id) => {
                const atom = atomMap[id];
                if (!atom) return null;
                return (
                  <div key={id} className="atom-card">
                    <p className="atom-text">{atom.text}</p>
                    <p className="atom-meta">{atom.speaker} · {atom.tags?.join(", ")}</p>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
