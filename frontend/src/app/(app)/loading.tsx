export default function Loading() {
return (
<div
className="page"
role="status"
aria-live="polite"
style={{
minHeight: "50vh",
display: "flex",
alignItems: "center",
justifyContent: "center",
flexDirection: "column",
gap: "12px",
}}
> <div className="spinner" /> <p className="text-muted">Loading your page...</p> </div>
);
}
