import type { FeatureCollection, Geometry } from "geojson";

export type Metric =
  | "tfr"
  | "children"
  | "childShare"
  | "childDensity"
  | "age0"
  | "age5"
  | "age10"
  | "change";
export type Bounds = [[number, number], [number, number]];
export interface Region {
  code: string;
  name: string;
  prefecture: string;
  prefCode: string;
  level: string;
  population: number | null;
  children: number | null;
  ages: [number | null, number | null, number | null];
  unknownAge: number | null;
  childShare: number | null;
  tfr: number | null;
  area: number | null;
  childDensity: number | null;
  population2015: number | null;
  change: number | null;
  bounds?: Bounds;
  center?: [number, number];
  /** Derived map membership for the 21 city/ward aggregates, never extra population rows. */
  memberCodes?: string[];
}
export interface Source {
  title: string;
  period: string;
  published: string;
  page: string;
  url: string;
  file: string;
  bytes: number;
  sha256: string;
}
export interface Statistics {
  metadata: {
    generatedAt: string;
    municipalityCount: number;
    geometryCount: number;
    missingTfr: string[];
    unmatchedGeometry: { code: string; name: string; prefecture: string }[];
    missingByMetric: Record<string, number>;
    sources: Source[];
    definitions: Record<string, string>;
  };
  national: Region;
  prefectures: Region[];
  municipalities: Region[];
  cities: Region[];
}
export interface GeoProperties {
  code: string;
  name: string;
  prefecture: string;
  city: string | null;
}
export type Geography = FeatureCollection<Geometry, GeoProperties>;
export interface FocusRequest {
  bounds: Bounds;
  key: number;
}
export interface MapPosition {
  lat: number;
  lng: number;
  zoom: number;
  source: string;
}
