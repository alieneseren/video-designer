export interface WhatsAppMessage {
  id: string | number;
  sender: "contact" | "user";
  text: string;
  time?: string;
  senderName?: string;
  senderAvatar?: string;
  senderColor?: string;
  startFrame: number;
  durationInFrames: number;
}

export interface WhatsAppVideoProps {
  contactName: string;
  contactAvatar?: string;
  statusText?: string;
  audioPath: string;
  bgmPath?: string;
  bgmVolume?: number;
  bgVideoPath?: string;
  layout?: "dublaj_style" | "compact_top" | "fullscreen" | "viral_chat";
  theme?: "light" | "dark";
  watermarkText?: string;
  instagramUsername?: string;
  wallpaperPath?: string;
  isGroup?: boolean;
  groupParticipants?: string;
  language?: string;
  messages: WhatsAppMessage[];
  fps: number;
  durationInFrames: number;
}

export interface WordHighlight {
  word: string;
  startFrame: number;
  endFrame: number;
}

export interface CaptionSegment {
  text: string;
  startFrame: number;
  durationInFrames: number;
  words?: WordHighlight[];
}

export interface RedditVideoProps {
  question: string;
  subreddit: string;
  author: string;
  upvotes: string;
  avatarPath?: string;
  bgVideoPath?: string;
  cardDurationFrames?: number;
  audioPath: string;
  bgmPath?: string;
  bgmVolume?: number;
  captions: CaptionSegment[];
  fps: number;
  durationInFrames: number;
}

export interface StoryScene {
  id: string | number;
  imagePath: string;
  captionText: string;
  startFrame: number;
  durationInFrames: number;
  cameraEffect?: "zoom_in" | "zoom_out" | "pan_left" | "pan_right" | "ken_burns" | "shake";
  transition?: "fade" | "slide_left" | "zoom_cut" | "page_turn";
  mood?: "dramatic" | "mysterious" | "happy" | "tense" | "peaceful";
  highlightWords?: string[];
}

export interface StoryIllustratedVideoProps {
  title: string;
  author?: string;
  scenes: StoryScene[];
  audioPath: string;
  bgmPath?: string;
  bgmVolume?: number;
  theme?: "cinematic_dark" | "comic_ink" | "fairytale" | "cozy_vintage";
  watermarkText?: string;
  fps: number;
  durationInFrames: number;
}

