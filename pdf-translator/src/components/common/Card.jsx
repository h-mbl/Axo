export function Card({ children, className = '', ...props }) {
  return (
    <div
      className={`bg-gray-900 border border-gray-800 rounded-lg p-6 ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}