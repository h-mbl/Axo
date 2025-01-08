export function Button({ children, variant = 'default', size = 'default', ...props }) {
  const variants = {
    default: 'bg-blue-500 hover:bg-blue-600 text-white',
    outline: 'border border-gray-600 hover:bg-gray-800',
    icon: 'p-2 hover:bg-gray-800 rounded-full'
  };

  const sizes = {
    default: 'px-4 py-2',
    sm: 'px-3 py-1 text-sm',
    lg: 'px-6 py-3 text-lg'
  };

  return (
    <button
      className={`rounded transition-colors ${variants[variant]} ${sizes[size]}`}
      {...props}
    >
      {children}
    </button>
  );
}