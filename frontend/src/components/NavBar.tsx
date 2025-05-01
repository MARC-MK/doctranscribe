import { Link, NavLink } from "react-router-dom";
import { Upload, LineChart } from "lucide-react";

function NavBar() {
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-1 px-3 py-2 rounded-md hover:bg-background text-sm ${
      isActive ? "bg-background-light text-primary" : "text-gray-300"
    }`;

  return (
    <header className="bg-background border-b border-background-light">
      <nav className="max-w-5xl mx-auto flex items-center justify-between p-4">
        <Link to="/upload" className="text-xl font-bold text-primary">
          DocTranscribe
        </Link>
        <div className="flex gap-4">
          <NavLink to="/upload" className={linkClass} end>
            <Upload size={16} /> Upload
          </NavLink>
          <NavLink to="/results" className={linkClass}>
            <LineChart size={16} /> Results
          </NavLink>
        </div>
      </nav>
    </header>
  );
}

export default NavBar; 