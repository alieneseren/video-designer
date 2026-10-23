import React from "react";
import { Composition } from "remotion";
import { WhatsAppVideo } from "./compositions/WhatsAppVideo";
import { RedditVideo } from "./compositions/RedditVideo";
import { ConnectomeClip, ConnectomeClipProps } from "./compositions/ConnectomeClip";
import { StoryIllustratedVideo } from "./compositions/StoryIllustratedVideo";
import { WhatsAppVideoProps, RedditVideoProps, StoryIllustratedVideoProps } from "./types";

interface ExtendedClipProps extends ConnectomeClipProps {
  totalFrames?: number;
  durationInFrames?: number;
}

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="WhatsAppChat"
        component={WhatsAppVideo as any}
        durationInFrames={900}
        fps={30}
        width={1080}
        height={1920}
        calculateMetadata={async ({ props }: { props: WhatsAppVideoProps }) => {
          return {
            durationInFrames: Math.max(30, props.durationInFrames || 900),
            fps: props.fps || 30,
          };
        }}
        defaultProps={{
          contactName: "Annem ❤️",
          statusText: "çevrimiçi",
          audioPath: "",
          messages: [
            {
              id: 1,
              sender: "contact" as const,
              text: "Oğlum eve gelirken ekmek al",
              time: "14:20",
              startFrame: 0,
              durationInFrames: 60,
            },
            {
              id: 2,
              sender: "user" as const,
              text: "Kaç tane alayım anne?",
              time: "14:21",
              startFrame: 65,
              durationInFrames: 50,
            },
          ],
          fps: 30,
          durationInFrames: 180,
        }}
      />

      <Composition
        id="RedditStory"
        component={RedditVideo as any}
        durationInFrames={1800}
        fps={30}
        width={1080}
        height={1920}
        calculateMetadata={async ({ props }: { props: RedditVideoProps }) => {
          return {
            durationInFrames: Math.max(30, props.durationInFrames || 1800),
            fps: props.fps || 30,
          };
        }}
        defaultProps={{
          question: "Hayatınızda tamamen tesadüfen öğrendiğiniz en tuhaf sır neydi?",
          subreddit: "r/AskReddit",
          author: "u/StoryTeller99",
          upvotes: "38.4k",
          audioPath: "",
          captions: [],
          fps: 30,
          durationInFrames: 300,
        }}
      />

      {/* Hikayeye Özel Çizim & Sinematik İllüstrasyon Videosu (Shorts - 9:16) */}
      <Composition
        id="StoryIllustrated"
        component={StoryIllustratedVideo as any}
        durationInFrames={900}
        fps={30}
        width={1080}
        height={1920}
        calculateMetadata={async ({ props }: { props: StoryIllustratedVideoProps }) => {
          const totalFrames =
            props.scenes && props.scenes.length > 0
              ? props.scenes.reduce(
                  (max, s) => Math.max(max, s.startFrame + s.durationInFrames),
                  30
                )
              : props.durationInFrames || 900;
          return {
            durationInFrames: Math.max(30, totalFrames),
            fps: props.fps || 30,
          };
        }}
        defaultProps={{
          title: "Karanlık Şehir Efsaneleri",
          author: "GizemliHikayeler",
          theme: "cinematic_dark" as const,
          audioPath: "",
          fps: 30,
          durationInFrames: 300,
          scenes: [
            {
              id: 1,
              imagePath: "media/sample_story_1.jpg",
              captionText: "Gece yarısı eski kütüphanenin kapısı aniden aralandı.",
              startFrame: 0,
              durationInFrames: 150,
              cameraEffect: "zoom_in" as const,
            },
            {
              id: 2,
              imagePath: "media/sample_story_2.jpg",
              captionText: "İçeride kimse yoktu, fakat raflardan bir fısıltı yükseliyordu.",
              startFrame: 150,
              durationInFrames: 150,
              cameraEffect: "pan_right" as const,
            },
          ],
        }}
      />

      {/* Sinek Beyni Biyo-AI Müzik (Shorts - 9:16) */}
      <Composition
        id="SinekKlipShort"
        component={ConnectomeClip as any}
        durationInFrames={900}
        fps={30}
        width={1080}
        height={1920}
        calculateMetadata={async ({ props }: { props: any }) => {
          return {
            durationInFrames: Math.max(30, props.totalFrames || props.durationInFrames || 900),
            props: {
              ...props,
              isVertical: true,
            },
          };
        }}
        defaultProps={{
          title: "AXONAL RESONANCE // SEQUENCE I",
          subtitle: "DROSOPHILA MELANOGASTER CONNECTOME SYNTHESIS",
          scale: "F Minor Pentatonic",
          bpm: 88,
          concept: "139.255 nöronluk biyolojik konnektom simülasyonu.",
          hook: "Meyve sineği beynindeki nöronların canlı piyano harmonikleri",
          theme: "cosmic",
          neuronsCount: 48,
          neuronCoords: [],
          spikes: [],
          isVertical: true,
          audioPath: "audio.wav",
        }}
      />

      {/* Sinek Beyni Biyo-AI Müzik (Uzun Klip 3-5 dk - 16:9 Landscape) */}
      <Composition
        id="SinekKlipLandscape"
        component={ConnectomeClip as any}
        durationInFrames={5400}
        fps={30}
        width={1920}
        height={1080}
        calculateMetadata={async ({ props }: { props: any }) => {
          return {
            durationInFrames: Math.max(30, props.totalFrames || props.durationInFrames || 5400),
            props: {
              ...props,
              isVertical: false,
            },
          };
        }}
        defaultProps={{
          title: "AXONAL RESONANCE // SEQUENCE I",
          subtitle: "DROSOPHILA MELANOGASTER CONNECTOME SYNTHESIS",
          scale: "F Minor Pentatonic",
          bpm: 88,
          concept: "139.255 nöronluk biyolojik konnektom simülasyonu.",
          hook: "Meyve sineği beynindeki nöronların canlı piyano harmonikleri",
          theme: "cosmic",
          neuronsCount: 48,
          neuronCoords: [],
          spikes: [],
          isVertical: false,
          audioPath: "audio.wav",
        }}
      />
    </>
  );
};
