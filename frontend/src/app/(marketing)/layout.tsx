"use client";

import { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Menu, X } from "lucide-react";
import SchematicBackground from "@/components/SchematicBackground";

const navLinks = [
  { href: "/use-cases", label: "Use Cases" },
  { href: "/pricing", label: "Pricing" },
  { href: "/blog", label: "Blog" },
  { href: "/docs", label: "Docs" },
  { href: "/about", label: "About" },
];

const footerLinks = {
  Product: [
    { href: "/use-cases", label: "Use Cases" },
    { href: "/pricing", label: "Pricing" },
    { href: "/changelog", label: "Changelog" },
    { href: "/docs", label: "Documentation" },
  ],
  Company: [
    { href: "/about", label: "About" },
    { href: "/blog", label: "Blog" },
    { href: "/contact", label: "Contact" },
  ],
  Legal: [
    { href: "/terms", label: "Terms of Service" },
    { href: "/privacy", label: "Privacy Policy" },
  ],
  Support: [
    { href: "/contact", label: "Contact Us" },
    { href: "/docs", label: "Documentation" },
    { href: "/testing", label: "Testing Guide" },
  ],
};

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-[#f5f0e8]">
      <SchematicBackground />
      {/* Navigation */}
      <nav className="sticky top-0 z-50 border-b border-[#1a1a1a] bg-[#0a0a0a]/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-12 flex items-center justify-between h-16">
          <Link href="/" className="flex items-center gap-2">
            <Image src="/bonito-icon.png" alt="Bonito" width={40} height={20} priority className="object-contain" />
            <span className="text-xl font-bold text-white">Bonito</span>
          </Link>
          
          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-8">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`text-sm transition ${
                  pathname === link.href ? "text-[#f5f0e8]" : "text-[#999] hover:text-[#f5f0e8]"
                }`}
              >
                {link.label}
              </Link>
            ))}
          </div>

          {/* Desktop Auth Buttons */}
          <div className="hidden md:flex items-center gap-4">
            <Link href="/login" className="text-sm text-[#999] hover:text-[#f5f0e8] transition">
              Sign In
            </Link>
            <Link
              href="/register"
              className="px-5 py-2.5 bg-[#7c3aed] hover:bg-[#6d28d9] text-white text-sm font-semibold rounded-lg transition"
            >
              Get Started
            </Link>
          </div>

          {/* Mobile Menu Button */}
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="md:hidden p-2 rounded-md hover:bg-[#1a1a1a] transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
            aria-label="Toggle mobile menu"
          >
            {isMobileMenuOpen ? (
              <X className="h-5 w-5" />
            ) : (
              <Menu className="h-5 w-5" />
            )}
          </button>
        </div>

        {/* Mobile Menu */}
        <AnimatePresence>
          {isMobileMenuOpen && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.2 }}
              className="md:hidden border-t border-[#1a1a1a] bg-[#0a0a0a]"
            >
              <div className="px-4 py-4 space-y-4">
                {navLinks.map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    onClick={() => setIsMobileMenuOpen(false)}
                    className={`block text-sm transition min-h-[44px] flex items-center ${
                      pathname === link.href ? "text-[#f5f0e8]" : "text-[#999] hover:text-[#f5f0e8]"
                    }`}
                  >
                    {link.label}
                  </Link>
                ))}
                <div className="pt-4 space-y-3 border-t border-[#1a1a1a]">
                  <Link 
                    href="/login" 
                    onClick={() => setIsMobileMenuOpen(false)}
                    className="block text-sm text-[#999] hover:text-[#f5f0e8] transition min-h-[44px] flex items-center"
                  >
                    Sign In
                  </Link>
                  <Link
                    href="/register"
                    onClick={() => setIsMobileMenuOpen(false)}
                    className="block w-full text-center px-5 py-3 bg-[#7c3aed] hover:bg-[#6d28d9] text-white text-sm font-semibold rounded-lg transition touch-manipulation"
                  >
                    Get Started
                  </Link>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </nav>

      {/* Content */}
      <motion.main
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="relative z-10"
      >
        {children}
      </motion.main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-[#1a1a1a] bg-[#0a0a0a]">
        <div className="max-w-7xl mx-auto px-4 md:px-6 lg:px-12 py-12 md:py-16">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-8">
            <div className="col-span-1 sm:col-span-2 lg:col-span-1">
              <Link href="/" className="flex items-center gap-3">
                <Image src="/bonito-icon.png" alt="Bonito" width={80} height={40} className="object-contain" />
                <span className="text-3xl font-bold text-white">Bonito</span>
              </Link>
              <p className="mt-4 text-sm text-[#666] leading-relaxed">
                The unified AI control plane for enterprise teams.
              </p>
            </div>
            {Object.entries(footerLinks).map(([category, links]) => (
              <div key={category}>
                <h4 className="text-sm font-semibold mb-4 text-[#999]">{category}</h4>
                <ul className="space-y-2.5">
                  {links.map((link) => (
                    <li key={link.href + link.label}>
                      <Link href={link.href} className="text-sm text-[#666] hover:text-[#f5f0e8] transition">
                        {link.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <div className="mt-12 pt-8 border-t border-[#1a1a1a] flex flex-col md:flex-row items-center justify-between gap-4">
            <p className="text-sm text-[#666]">© 2026 Bonito. All rights reserved.</p>
            <p className="text-sm text-[#444]">getbonito.com</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
