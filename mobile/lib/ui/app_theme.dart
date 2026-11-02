import 'package:flutter/material.dart';

import '../theme/ibh_tokens.dart';

/// The design-system theme plus the pieces the Android screens add: white bottom sheets with a
/// rounded top, dialogs with the card radius, and a snackbar action in the light accent so it can be
/// read on navy. `theme/ibh_tokens.dart` stays exactly as the design package ships it.
ThemeData ibhAppTheme() => ibhTheme().copyWith(
      bottomSheetTheme: const BottomSheetThemeData(
        backgroundColor: IbhColors.white,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(IbhRadius.sheet))),
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: IbhColors.white,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(IbhRadius.dialog)),
      ),
      snackBarTheme: SnackBarThemeData(
        backgroundColor: IbhColors.navy900,
        actionTextColor: IbhColors.focusOnDark,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(IbhRadius.control)),
        contentTextStyle: const TextStyle(fontFamily: 'Inter', fontSize: 15, color: IbhColors.white),
      ),
    );
