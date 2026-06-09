"use client";

/**
 * OrigamiCraneWatermark — origami paper crane silhouette used as a
 * faded background watermark inside the Origami chat surface.
 *
 * The path data is the exact crane outline Shabari provided (potrace
 * vectorisation of an orizuru illustration). We render it at the
 * caller's opacity + color tint.
 */

interface Props {
  /** Pixel size of the crane (square). Default 320. */
  size?: number;
  /** Fill color (any CSS color). Default white. */
  color?: string;
  /** Watermark opacity (0-1). Default 0.10. */
  opacity?: number;
  className?: string;
}

export function OrigamiCraneWatermark({
  size = 320,
  color = "#ffffff",
  opacity = 0.10,
  className = "",
}: Props) {
  return (
    <div
      className={`absolute inset-0 flex items-center justify-center pointer-events-none select-none z-0 ${className}`}
      aria-hidden="true"
    >
      <svg
        viewBox="0 0 2600 2600"
        width={size}
        height={size}
        preserveAspectRatio="xMidYMid meet"
        className="origami-crane-watermark"
        style={{ opacity }}
      >
        <g
          transform="translate(0,2600) scale(0.1,-0.1)"
          fill={color}
          stroke="none"
        >
          <path d="M16939 20752 c-69 -23 -135 -67 -186 -126 -30 -35 -480 -952 -1918 -3919 l-1879 -3874 -312 -168 c-172 -93 -316 -168 -320 -167 -5 1 -174 1103 -375 2449 -205 1365 -375 2472 -385 2502 -38 113 -145 216 -266 257 -35 12 -80 18 -133 17 -76 0 -102 -8 -490 -140 -225 -77 -434 -153 -464 -169 -59 -32 -2426 -1920 -2477 -1975 -76 -83 -109 -181 -102 -304 10 -197 159 -356 360 -385 35 -5 451 -10 926 -10 l862 0 0 -42 c0 -24 9 -394 21 -822 11 -428 19 -789 17 -801 -3 -21 -17 -19 -2928 342 -2142 266 -2942 362 -2990 359 -354 -25 -519 -460 -267 -706 29 -28 827 -624 1775 -1324 l1723 -1273 827 -951 827 -951 629 -1358 c346 -747 645 -1383 666 -1413 48 -73 115 -121 208 -153 116 -40 940 -161 1043 -154 66 4 425 115 2557 791 l2481 787 2783 -921 c1531 -506 2810 -925 2844 -932 170 -31 350 64 431 228 31 64 37 88 41 158 5 101 -13 172 -67 260 -20 33 -824 1276 -1785 2761 -1906 2946 -1803 2795 -1932 2846 -49 19 -77 23 -164 23 l-105 0 -1150 -456 c-632 -251 -1151 -453 -1153 -450 -1 4 306 2184 683 4845 377 2660 688 4863 691 4895 17 159 -79 323 -233 399 -68 33 -84 37 -167 40 -68 2 -105 -2 -147 -15z m-1144 -6412 c-266 -1878 -485 -3426 -487 -3440 -3 -20 -130 119 -764 830 -419 470 -763 859 -765 864 -3 7 2493 5166 2498 5162 1 0 -216 -1538 -482 -3416z m-4964 2408 c0 -2 236 -1573 523 -3491 l523 -3488 -440 -1692 c-241 -931 -441 -1694 -443 -1696 -5 -5 -153 14 -159 21 -3 2 -54 1968 -115 4369 -115 4560 -112 4470 -156 4564 -27 58 -90 129 -150 170 -105 72 -132 75 -692 75 l-485 0 687 549 687 550 102 35 c100 34 116 38 118 34z m-3151 -4274 c1185 -146 2157 -268 2159 -270 5 -5 112 -4097 108 -4128 -1 -11 -98 187 -215 440 -117 252 -228 483 -247 513 -29 46 -1690 1963 -1775 2048 -18 18 -523 396 -1124 839 -600 444 -1098 813 -1106 821 -13 13 -11 14 15 9 17 -3 1000 -125 2185 -272z m6415 -1498 c678 -761 906 -1023 899 -1033 -13 -21 -2908 -2733 -2912 -2729 -2 2 138 550 311 1218 213 818 317 1237 321 1288 5 65 -13 201 -129 979 -74 497 -133 907 -129 910 11 11 719 390 725 388 3 -1 415 -461 914 -1021z m5609 -2485 c740 -1144 1346 -2081 1346 -2084 0 -2 -712 232 -1582 520 -2822 934 -3010 995 -3070 1000 -31 3 -78 0 -105 -6 -26 -7 -786 -246 -1687 -532 -902 -286 -1643 -518 -1647 -517 -4 2 638 608 1427 1348 l1435 1345 1267 502 c697 276 1268 502 1269 502 0 1 607 -935 1347 -2078z" />
        </g>

        <style>{`
          .origami-crane-watermark {
            transform-origin: 50% 50%;
            animation: crane-watermark-breathe 9s ease-in-out infinite;
          }
          @keyframes crane-watermark-breathe {
            0%, 100% { transform: scale(1) translateY(0); }
            50%      { transform: scale(1.02) translateY(-3px); }
          }
          @media (prefers-reduced-motion: reduce) {
            .origami-crane-watermark { animation: none; }
          }
        `}</style>
      </svg>
    </div>
  );
}
