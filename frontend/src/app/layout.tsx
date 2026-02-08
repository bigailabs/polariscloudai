import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import { ToastProvider } from "@/components/toast";
import { ConfirmDialogProvider } from "@/components/confirm-dialog";
import { PostHogWrapper } from "@/components/posthog-provider";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Polaris Computer",
  description: "Cloud compute platform — deploy AI models in seconds",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider
      appearance={{
        variables: {
          colorPrimary: "#2D5A47",
          colorText: "#1B3D2F",
          colorTextOnPrimaryBackground: "#FFFFFF",
          colorTextSecondary: "#4A7C59",
          colorBackground: "#F7FAF8",
          colorInputBackground: "#FFFFFF",
          colorInputText: "#1B3D2F",
          colorDanger: "#DC2626",
          colorSuccess: "#4A7C59",
          colorWarning: "#B87333",
          colorNeutral: "#1B3D2F",
          borderRadius: "0.5rem",
          fontFamily: "Inter, system-ui, sans-serif",
        },
        elements: {
          formButtonPrimary: "bg-[#2D5A47] hover:bg-[#234338] text-white shadow-none",
          footerActionLink: "text-[#2D5A47] hover:text-[#234338]",
          card: "shadow-lg",
          headerTitle: "text-[#1B3D2F]",
          headerSubtitle: "text-[#1B3D2F]/70",
          socialButtonsBlockButton: "border-[#E8EFEB] text-[#1B3D2F] hover:bg-[#F7FAF8]",
          formFieldLabel: "text-[#1B3D2F]",
          formFieldInput: "border-[#E8EFEB] focus:border-[#2D5A47] focus:ring-[#2D5A47]",
          identityPreview: "border-[#E8EFEB]",
          identityPreviewText: "text-[#1B3D2F]",
          identityPreviewEditButton: "text-[#2D5A47]",
          userButtonPopoverCard: "border-[#E8EFEB] shadow-lg",
          userButtonPopoverActionButton: "text-[#1B3D2F] hover:bg-[#F7FAF8]",
          userButtonPopoverActionButtonText: "text-[#1B3D2F]",
          userButtonPopoverActionButtonIcon: "text-[#1B3D2F]/60",
          userButtonPopoverFooter: "hidden",
          userPreviewMainIdentifier: "text-[#1B3D2F] font-medium",
          userPreviewSecondaryIdentifier: "text-[#1B3D2F]/70",
          avatarBox: "border-[#E8EFEB]",
        },
      }}
    >
      <html lang="en">
        <body
          className={`${inter.variable} ${jetbrainsMono.variable} antialiased`}
        >
          <PostHogWrapper>
            <ToastProvider>
              <ConfirmDialogProvider>{children}</ConfirmDialogProvider>
            </ToastProvider>
          </PostHogWrapper>
        </body>
      </html>
    </ClerkProvider>
  );
}
